"""Helpers shared by administrative routes."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.audit import AuditOutcome
from app.services.audit_service import AuditEventType, record_audit_event
from app.services.identity.context import AuthContext


@contextmanager
def audit_denials(db: Session, auth: AuthContext, meta: RequestMeta, action: str) -> Iterator[None]:
    """Record refused administrative actions (403) for security monitoring.

    The failed operation's changes are rolled back first; only the denial is kept.
    """
    actor_id = auth.user.id
    try:
        yield
    except AppError as exc:
        if exc.status_code == 403:
            db.rollback()
            record_audit_event(
                db,
                event_type=AuditEventType.AUTHORIZATION_DENIED,
                outcome=AuditOutcome.DENIED,
                meta=meta,
                actor_user_id=actor_id,
                metadata={"action": action, "code": exc.code},
            )
            db.commit()
        raise
