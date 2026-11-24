"""The signed-in user's notification centre (first release, migration 0011).

Every signed-in user may read and manage only their own notifications; no extra
permission is needed. Opening the list first creates any reminders that have fallen
due for the user's linked employee (idempotent). Reminders for everyone - including
people who are not signed in - are created by the scheduled job
``python -m app.jobs training-reminders`` (run by the OS scheduler; see app/jobs.py).
``POST /notifications/reminders/run`` lets an administrator trigger the same run.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    AuthContextDep,
    DbSessionDep,
    SettingsDep,
    require_permission,
    require_schema,
)
from app.core.errors import AppError
from app.schemas.errors import ErrorResponse
from app.schemas.training import (
    ChannelOut,
    ChannelsOut,
    NotificationList,
    NotificationOut,
    NotificationRead,
    PreferencesOut,
    PreferenceUpdate,
)
from app.services import notifications
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(require_schema("0011"))],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)


def _active(auth: AuthContextDep) -> AuthContext:
    if auth.user.password_must_change:
        raise AppError(
            403, "password_change_required", "You must change your password before continuing."
        )
    return auth


SignedIn = Annotated[AuthContext, Depends(_active)]


@router.get("", response_model=NotificationList, summary="My notifications (newest first)")
def list_notifications(
    auth: SignedIn,
    db: DbSessionDep,
    settings: SettingsDep,
    unread_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> NotificationList:
    if auth.user.employee_id is not None and notifications.generate_due_reminders(
        db,
        offsets=settings.reminder_offsets,
        settings=settings,
        employee_id=auth.user.employee_id,
    ):
        db.commit()
    items, unread = notifications.list_for_user(
        db, auth.user.id, unread_only=unread_only, limit=limit
    )
    return NotificationList(
        items=[NotificationOut.model_validate(i, from_attributes=True) for i in items],
        unread_count=unread,
    )


@router.post("/{public_id}/read", response_model=NotificationOut, summary="Mark read or unread")
def mark_read(
    public_id: uuid.UUID, body: NotificationRead, auth: SignedIn, db: DbSessionDep
) -> NotificationOut:
    item = notifications.mark_read(db, auth.user.id, public_id, read=body.read)
    db.commit()
    return NotificationOut.model_validate(item, from_attributes=True)


@router.post("/read-all", response_model=dict[str, int], summary="Mark all as read")
def mark_all_read(auth: SignedIn, db: DbSessionDep) -> dict[str, int]:
    count = notifications.mark_all_read(db, auth.user.id)
    db.commit()
    return {"marked": count}


@router.get("/preferences", response_model=PreferencesOut, summary="My notification preferences")
def get_preferences(auth: SignedIn, db: DbSessionDep) -> PreferencesOut:
    return PreferencesOut(
        preferences=notifications.preferences(db, auth.user.id),
        mandatory=sorted(notifications.MANDATORY_TYPES),
    )


@router.put("/preferences", response_model=PreferencesOut, summary="Switch a notification type")
def set_preference(body: PreferenceUpdate, auth: SignedIn, db: DbSessionDep) -> PreferencesOut:
    prefs = notifications.set_preference(
        db, auth.user.id, body.notification_type, body.in_app_enabled
    )
    db.commit()
    return PreferencesOut(preferences=prefs, mandatory=sorted(notifications.MANDATORY_TYPES))


@router.get("/channels", response_model=ChannelsOut, summary="Delivery channels and their status")
def channels(_auth: SignedIn, settings: SettingsDep) -> ChannelsOut:
    return ChannelsOut(
        channels=[
            ChannelOut(code=c.code, name=c.name, connected=c.connected, detail=c.detail)
            for c in (notifications.IN_APP_CHANNEL, *notifications.EXTERNAL_CHANNELS)
        ],
        reminder_offsets_days=list(settings.reminder_offsets),
    )


@router.post(
    "/reminders/run",
    response_model=dict[str, int],
    summary="Generate due training reminders for everyone (idempotent)",
)
def run_reminders(
    _auth: Annotated[AuthContext, Depends(require_permission(Permission.TRAINING_EVENTS_MANAGE))],
    db: DbSessionDep,
    settings: SettingsDep,
) -> dict[str, int]:
    created = notifications.generate_due_reminders(
        db, offsets=settings.reminder_offsets, settings=settings
    )
    db.commit()
    return {"created": created}
