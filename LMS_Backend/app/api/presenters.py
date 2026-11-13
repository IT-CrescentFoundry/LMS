"""Convert ORM objects into response schemas (keeps route handlers thin)."""

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security.tokens import csrf_token_for
from app.models.audit import AuditEvent
from app.models.identity import AccessRole, UserAccessRole, UserAccount, UserSession
from app.schemas.access import AccessRoleOut, PermissionOut
from app.schemas.audit import AuditActorOut, AuditEventOut
from app.schemas.auth import CurrentUser, SessionResponse
from app.schemas.users import RoleGrantOut, SessionOut, UserDetail, UserSummary
from app.services.identity.access_control import active_grants
from app.services.identity.context import AuthContext


def current_user(auth: AuthContext) -> CurrentUser:
    user = auth.user
    return CurrentUser(
        public_id=user.public_id,
        login_id=user.login_id,
        display_name=user.display_name,
        email=user.email,
        status=user.status,
        password_must_change=user.password_must_change,
        roles=list(auth.roles),
        permissions=sorted(auth.permissions),
    )


def session_response(auth: AuthContext, settings: Settings) -> SessionResponse:
    return SessionResponse(
        authenticated=True,
        user=current_user(auth),
        csrf_token=csrf_token_for(settings.secret_key, auth.session.token_hash),
        idle_expires_at=auth.session.idle_expires_at,
        absolute_expires_at=auth.session.absolute_expires_at,
    )


def roles_by_user(db: Session, user_ids: Sequence[int]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = defaultdict(list)
    if not user_ids:
        return result
    rows = db.execute(
        select(UserAccessRole.user_account_id, AccessRole.code)
        .join(AccessRole, AccessRole.id == UserAccessRole.access_role_id)
        .where(UserAccessRole.user_account_id.in_(user_ids), UserAccessRole.revoked_at.is_(None))
        .order_by(AccessRole.code)
    )
    for user_id, code in rows:
        result[user_id].append(code)
    return result


def user_summaries(db: Session, accounts: Sequence[UserAccount]) -> list[UserSummary]:
    roles = roles_by_user(db, [account.id for account in accounts])
    return [
        UserSummary(
            public_id=account.public_id,
            login_id=account.login_id,
            display_name=account.display_name,
            email=account.email,
            status=account.status,
            roles=roles.get(account.id, []),
            last_login_at=account.last_login_at,
            created_at=account.created_at,
        )
        for account in accounts
    ]


def user_detail(db: Session, account: UserAccount) -> UserDetail:
    grants = active_grants(db, account.id)
    return UserDetail(
        public_id=account.public_id,
        login_id=account.login_id,
        display_name=account.display_name,
        email=account.email,
        status=account.status,
        roles=sorted(grant.role.code for grant in grants),
        last_login_at=account.last_login_at,
        created_at=account.created_at,
        password_must_change=account.password_must_change,
        status_changed_at=account.status_changed_at,
        status_reason=account.status_reason,
        activated_at=account.activated_at,
        deactivated_at=account.deactivated_at,
        password_changed_at=account.password_changed_at,
        role_grants=[
            RoleGrantOut(role=grant.role.code, granted_at=grant.granted_at) for grant in grants
        ],
    )


def session_out(record: UserSession) -> SessionOut:
    return SessionOut(
        public_id=record.public_id,
        created_at=record.created_at,
        last_seen_at=record.last_seen_at,
        idle_expires_at=record.idle_expires_at,
        absolute_expires_at=record.absolute_expires_at,
        ip_address=record.ip_address,
        user_agent=record.user_agent,
    )


def role_out(role: AccessRole) -> AccessRoleOut:
    return AccessRoleOut(
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        is_api_assignable=role.is_api_assignable,
        assign_permission=role.assign_permission.code if role.assign_permission else None,
        permissions=[permission.code for permission in role.permissions],
    )


def permission_out(code: str, description: str, is_privileged: bool) -> PermissionOut:
    return PermissionOut(code=code, description=description, is_privileged=is_privileged)


def audit_events_out(db: Session, events: Sequence[AuditEvent]) -> list[AuditEventOut]:
    actor_ids = {event.actor_user_id for event in events if event.actor_user_id is not None}
    actors: dict[int, UserAccount] = {}
    if actor_ids:
        actors = {
            account.id: account
            for account in db.scalars(select(UserAccount).where(UserAccount.id.in_(actor_ids)))
        }
    output: list[AuditEventOut] = []
    for event in events:
        actor = actors.get(event.actor_user_id) if event.actor_user_id is not None else None
        output.append(
            AuditEventOut(
                event_id=event.public_id,
                occurred_at=event.occurred_at,
                event_type=event.event_type,
                outcome=event.outcome,
                actor=AuditActorOut(
                    public_id=actor.public_id,
                    login_id=actor.login_id,
                    display_name=actor.display_name,
                )
                if actor
                else None,
                target_type=event.target_type,
                target_id=event.target_id,
                request_id=event.request_id,
                source_ip=event.source_ip,
                user_agent=event.user_agent,
                metadata=event.event_metadata,
            )
        )
    return output
