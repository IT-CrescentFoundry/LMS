"""Read-only audit log API. There are deliberately no update or delete endpoints."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSessionDep, RequestMetaDep, require_permission
from app.api.presenters import audit_events_out
from app.models.audit import AuditOutcome
from app.schemas.audit import AuditEventOut
from app.schemas.errors import ErrorResponse
from app.schemas.pagination import Page
from app.services.audit_queries import AuditFilters, list_audit_events
from app.services.audit_service import AuditEventType, record_audit_event
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission

router = APIRouter(
    prefix="/admin/audit-events",
    tags=["administration: audit"],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)

ViewAudit = Annotated[AuthContext, Depends(require_permission(Permission.AUDIT_VIEW))]


@router.get("", response_model=Page[AuditEventOut], summary="List audit events (newest first)")
def list_events(
    auth: ViewAudit,
    db: DbSessionDep,
    meta: RequestMetaDep,
    event_type: Annotated[str | None, Query(max_length=100)] = None,
    outcome: AuditOutcome | None = None,
    actor: uuid.UUID | None = None,
    target_type: Annotated[str | None, Query(max_length=50)] = None,
    target_id: Annotated[str | None, Query(max_length=64)] = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[AuditEventOut]:
    filters = AuditFilters(
        event_type=event_type,
        outcome=outcome,
        actor_public_id=actor,
        target_type=target_type,
        target_id=target_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    events, next_cursor = list_audit_events(db, filters, limit=limit, cursor=cursor)
    page = Page[AuditEventOut](items=audit_events_out(db, events), next_cursor=next_cursor)
    record_audit_event(
        db,
        event_type=AuditEventType.AUDIT_VIEWED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=auth.user.id,
        metadata={
            "filters": {
                key: str(value) for key, value in vars(filters).items() if value is not None
            },
            "first_page": cursor is None,
        },
    )
    db.commit()
    return page
