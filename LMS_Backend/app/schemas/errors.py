"""Standard error envelope returned by every API error response."""

from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    location: list[str] = Field(description="Path to the invalid field, e.g. ['body', 'name'].")
    message: str
    type: str


class ErrorBody(BaseModel):
    code: str = Field(description="Stable, machine-readable error code.")
    message: str = Field(description="Human-readable summary, safe to display.")
    details: list[ValidationIssue] | None = None
    request_id: str | None = Field(
        default=None, description="Correlates the error with server-side logs."
    )


class ErrorResponse(BaseModel):
    error: ErrorBody
