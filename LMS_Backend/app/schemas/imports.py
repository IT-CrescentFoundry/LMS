"""Import API schemas (Stage D). Workbook *cell values* appear only in staged rows and
issues of a job (mapped fields only), never in audit metadata or logs."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.audit import AuditActorOut
from app.schemas.organisation import RefOut, Version

Reason = str


class ProfileFieldOut(BaseModel):
    name: str
    type: str
    required: bool
    aliases: list[str]
    reference: str | None


class ProfileSectionOut(BaseModel):
    kind: str
    sheet_aliases: list[str]
    natural_key: list[str]
    fields: list[ProfileFieldOut]


class ImportProfileOut(BaseModel):
    code: str
    version: int
    commit_mode: str
    sections: list[ProfileSectionOut]
    can_run: bool
    can_commit: bool


class HeaderOut(BaseModel):
    column: str
    index: int
    text: str
    excluded: bool
    suggested_field: str | None


class SheetOut(BaseModel):
    name: str
    state: str
    dimensions: str | None
    suggested_section: str | None
    header_row: int | None
    headers: list[HeaderOut]


class MappingSectionOut(BaseModel):
    section: str
    sheet: str
    header_row: int
    columns: dict[str, str] = Field(description="1-based column index -> profile field.")


class ImportJobSummary(BaseModel):
    public_id: uuid.UUID
    profile_code: str
    profile_version: int
    status: str
    original_filename: str
    file_size: int
    uploaded_by: AuditActorOut | None
    uploaded_at: datetime
    validated_at: datetime | None
    committed_at: datetime | None
    finished_at: datetime | None
    counts: dict[str, Any]


class ImportJobOut(ImportJobSummary):
    file_sha256: str
    file_stored: bool
    workbook: list[SheetOut]
    column_mapping: list[MappingSectionOut]
    mapping_confirmed: bool
    previously_imported_by: list[uuid.UUID]
    failure_code: str | None
    validated_by: AuditActorOut | None
    committed_by: AuditActorOut | None
    version: int


class IssueOut(BaseModel):
    id: int
    section: str | None
    sheet: str | None
    row_number: int | None
    column: str | None
    field: str | None
    code: str
    severity: Literal["error", "warning"]
    source_value: str | None
    params: dict[str, Any] | None


class RowOut(BaseModel):
    id: int
    section: str
    sheet: str
    row_number: int
    outcome: str
    values: dict[str, Any]
    source: dict[str, Any]
    changes: dict[str, Any] | None
    decision: str | None
    decision_reason: str | None
    target_public_id: uuid.UUID | None
    issues: list[IssueOut]


class SuggestionOut(BaseModel):
    public_id: uuid.UUID
    code: str
    label: str
    score: int
    reason: str


class ValueMappingOut(BaseModel):
    public_id: uuid.UUID
    kind: str
    source_text: str
    normalised_text: str
    status: str
    target: RefOut | None
    decision_reason: str | None
    decided_by: AuditActorOut | None
    decided_at: datetime | None
    created_at: datetime
    suggestions: list[SuggestionOut]
    version: int


# ---------------------------------------------------------------------- request bodies


class MappingSectionIn(BaseModel):
    section: str = Field(max_length=30)
    sheet: str = Field(max_length=100)
    header_row: int = Field(ge=1, le=50)
    columns: dict[str, str] = Field(max_length=200)


class MappingIn(BaseModel):
    version: Version
    sections: list[MappingSectionIn] = Field(min_length=1, max_length=30)


class VersionIn(BaseModel):
    version: Version


class RowDecisionIn(BaseModel):
    version: Version
    decision: Literal["skip", "distinct"] | None
    reason: str | None = Field(default=None, max_length=500)


class CommitIn(BaseModel):
    version: Version
    confirm: Literal[True] = Field(description="Must be true: the explicit approval.")
    apply_updates: bool = Field(
        default=False,
        description="Apply the listed corrections to existing employees (otherwise skipped).",
    )


class ApproveMappingIn(BaseModel):
    version: Version
    target_public_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


class MappingDecisionIn(BaseModel):
    version: Version
    reason: str | None = Field(default=None, max_length=500)
