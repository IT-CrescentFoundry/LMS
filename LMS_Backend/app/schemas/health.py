"""Health-check response schemas."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    version: str
    timestamp: datetime


class CheckStatus(StrEnum):
    OK = "ok"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"


class ComponentCheck(BaseModel):
    status: CheckStatus
    detail: str | None = Field(default=None, description="Safe, non-sensitive explanation.")
    duration_ms: float | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, ComponentCheck]
    timestamp: datetime
