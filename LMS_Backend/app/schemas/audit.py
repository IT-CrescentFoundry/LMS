"""Read-only audit event schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditActorOut(BaseModel):
    public_id: uuid.UUID
    login_id: str
    display_name: str


class AuditEventOut(BaseModel):
    event_id: uuid.UUID
    occurred_at: datetime
    event_type: str
    outcome: str
    actor: AuditActorOut | None
    target_type: str | None
    target_id: str | None
    request_id: str | None
    source_ip: str | None
    user_agent: str | None
    metadata: dict[str, Any] | None
