"""Employee master schemas (Stage C3).

Employees are separate from login accounts (ADR-040). No schema carries
compensation, government identifiers, date of birth, gender, home address, health,
family or personal contact information; those fields do not exist in the LMS.

Changes to an existing record carry its ``version``. PATCH bodies are partial.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, Field

from app.schemas.audit import AuditEventOut
from app.schemas.organisation import PatchModel, Reason, RefOut, Version, WarningOut

EmployeeCode = Annotated[
    str,
    Field(
        min_length=1,
        max_length=30,
        description="Trimmed and stored in capitals; letters, digits, '/', '.', '_' and '-'. "
        "Always text: leading zeros are kept.",
    ),
]
PersonName = Annotated[str, Field(min_length=1, max_length=200)]
WorkEmail = Annotated[str, Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Language = Literal["en", "bn", "hi", "gu"]
StatusValue = Literal["active", "on_leave", "separated"]
StatusFilter = Literal["active", "on_leave", "separated", "unknown"]
AssignmentTypeValue = Literal["primary", "additional", "acting", "deputation"]
EndReason = Annotated[str, Field(max_length=500)]


class EmployeeRef(BaseModel):
    public_id: uuid.UUID
    employee_code: str
    full_name: str
    employment_status: StatusValue | None


class AccountRef(BaseModel):
    """A linked login account (never includes credentials or tokens)."""

    public_id: uuid.UUID
    login_id: str
    display_name: str
    status: str


# --------------------------------------------------------------------- employees


class EmployeeSummary(BaseModel):
    public_id: uuid.UUID
    employee_code: str
    full_name: str
    display_name: str | None
    employment_status: StatusValue | None = Field(description="Null means not recorded.")
    as_of: date
    primary_unit: RefOut | None
    path: list[RefOut] = Field(description="Ancestors of the primary unit, root first.")
    designation: RefOut | None
    location: RefOut | None
    line_manager: EmployeeRef | None
    has_active_account: bool


class EmployeeOut(EmployeeSummary):
    preferred_language: Language | None
    work_email: str | None
    date_of_joining: date | None
    date_of_separation: date | None = Field(description="Last working day.")
    external_ref: str | None
    accounts: list[AccountRef]
    version: int
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    employee_code: EmployeeCode
    full_name: PersonName
    display_name: PersonName | None = None
    preferred_language: Language | None = None
    work_email: WorkEmail | None = None
    employment_status: StatusValue | None = Field(
        default=None, description="Leave empty when the status has not been recorded."
    )
    date_of_joining: date | None = None
    date_of_separation: date | None = None
    external_ref: Annotated[str, Field(max_length=100)] | None = None


class EmployeeCorrect(PatchModel):
    """Correction of wrongly recorded data. Status changes use employment-status."""

    required_if_sent: ClassVar[tuple[str, ...]] = ("employee_code", "full_name")

    version: Version
    reason: Reason | None = None
    employee_code: EmployeeCode | None = None
    full_name: PersonName | None = None
    display_name: PersonName | None = None
    preferred_language: Language | None = None
    work_email: WorkEmail | None = None
    date_of_joining: date | None = None
    external_ref: Annotated[str, Field(max_length=100)] | None = None


SeparationRecordKind = Literal["assignment", "functional_role", "responsibility", "reporting_line"]


class SeparationRecordOut(BaseModel):
    """One of the employee's own records that continues after the last working day."""

    record_id: uuid.UUID
    kind: SeparationRecordKind
    code: str = Field(description="Unit, role or responsibility code; manager's employee code.")
    name: str
    effective_from: date | None
    effective_to: date | None
    starts_after_separation: bool = Field(
        description="Starts after the last working day: cannot be ended by separation."
    )


class DirectReportOut(BaseModel):
    """A reporting line in which the employee is the MANAGER."""

    record_id: uuid.UUID
    employee: EmployeeRef = Field(description="The subordinate.")
    relationship_type: RefOut
    effective_from: date | None
    effective_to: date | None
    starts_after_separation: bool


class SeparationPreviewOut(BaseModel):
    """Read-only impact of separating on ``separation_date``; nothing is changed."""

    employee: EmployeeRef
    version: int
    separation_date: date = Field(description="Last working day, exactly as requested.")
    records_end_on: date = Field(
        description="The effective_to ended records would get: the day after the last "
        "working day (end dates are exclusive)."
    )
    own_records: list[SeparationRecordOut]
    direct_reports: list[DirectReportOut]
    requires_end_open_records: bool = Field(
        description="Own records would be ended: the request needs end_open_records."
    )
    requires_end_direct_reports: bool = Field(
        description="Direct reports' lines would be ended: the request needs end_direct_reports."
    )
    blocked: bool = Field(
        description="A record starts after the last working day; separation would be refused."
    )


class EmploymentStatusChange(BaseModel):
    version: Version
    status: StatusValue
    separation_date: date | None = Field(
        default=None,
        description="Last working day; required for separated. Records end on the "
        "following day (effective_to is exclusive).",
    )
    end_open_records: bool = Field(
        default=False,
        description="End the employee's own assignments, roles, responsibilities and "
        "reporting lines (as subordinate) that continue after the separation date.",
    )
    end_direct_reports: bool = Field(
        default=False,
        description="End the reporting lines of the employee's direct reports (the "
        "employee as manager) on the same date; each is audited on the subordinate.",
    )
    reason: Reason | None = None


# ------------------------------------------------------------------- assignments


class AssignmentOut(BaseModel):
    public_id: uuid.UUID
    assignment_type: AssignmentTypeValue
    org_unit: RefOut
    designation: RefOut | None
    grade: RefOut | None
    job_level: RefOut | None
    location: RefOut | None
    effective_from: date | None = Field(description="Null means the start was not recorded.")
    effective_to: date | None = Field(description="Exclusive end; null while open.")
    source: str
    reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class AssignmentWriteOut(BaseModel):
    assignment: AssignmentOut
    warnings: list[WarningOut]


class AssignmentCreate(BaseModel):
    assignment_type: AssignmentTypeValue = "primary"
    org_unit_id: uuid.UUID
    designation_id: uuid.UUID | None = None
    grade_id: uuid.UUID | None = None
    job_level_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: Reason | None = None


class AssignmentChange(PatchModel):
    """Business change from ``effective_date`` (transfer, designation, grade, ...)."""

    required_if_sent: ClassVar[tuple[str, ...]] = ("org_unit_id",)

    version: Version
    effective_date: date
    reason: Reason | None = None
    org_unit_id: uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    grade_id: uuid.UUID | None = None
    job_level_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None


class AssignmentCorrect(PatchModel):
    required_if_sent: ClassVar[tuple[str, ...]] = ("org_unit_id", "assignment_type")

    version: Version
    reason: Reason | None = None
    assignment_type: AssignmentTypeValue | None = None
    org_unit_id: uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    grade_id: uuid.UUID | None = None
    job_level_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class AssignmentEnd(BaseModel):
    version: Version
    effective_to: date = Field(description="Exclusive end date.")
    reason: Reason | None = None


class RecordEnd(BaseModel):
    effective_to: date = Field(description="Exclusive end date.")
    reason: EndReason | None = None


# ------------------------------------------------------------- functional roles


class DerivedFromOut(BaseModel):
    assignment: uuid.UUID
    assignment_type: AssignmentTypeValue
    org_unit: RefOut
    designation: RefOut
    mapping: uuid.UUID


class RoleRecordOut(BaseModel):
    public_id: uuid.UUID
    functional_role: RefOut
    kind: Literal["manual", "exclusion"]
    effective_from: date | None
    effective_to: date | None
    reason: str | None
    created_at: datetime


class EffectiveRoleOut(BaseModel):
    functional_role: RefOut
    effective: bool = Field(description="False when an exclusion hides the role.")
    derived_from: list[DerivedFromOut]
    manual: RoleRecordOut | None
    exclusion: RoleRecordOut | None


class FunctionalRolesOut(BaseModel):
    as_of: date
    roles: list[EffectiveRoleOut]
    records: list[RoleRecordOut] = Field(description="Manual and exclusion records.")


class RoleAssign(BaseModel):
    functional_role_id: uuid.UUID
    kind: Literal["manual", "exclusion"] = "manual"
    effective_from: date | None = None
    effective_to: date | None = None
    reason: Reason | None = None


# ------------------------------------------------------------- responsibilities


class ResponsibilityRecordOut(BaseModel):
    public_id: uuid.UUID
    responsibility: RefOut
    context_unit: RefOut | None
    context_location: RefOut | None
    effective_from: date | None
    effective_to: date | None
    reason: str | None
    created_at: datetime


class ResponsibilityAssign(BaseModel):
    responsibility_id: uuid.UUID
    context_unit_id: uuid.UUID | None = None
    context_location_id: uuid.UUID | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    reason: Reason | None = None


# -------------------------------------------------------------------- reporting


class ReportingTypeOut(BaseModel):
    public_id: uuid.UUID
    code: str
    name: str
    allows_multiple: bool
    is_hierarchical: bool
    is_active: bool
    translations: dict[str, str]


class ReportingRecordOut(BaseModel):
    public_id: uuid.UUID
    relationship_type: RefOut
    employee: EmployeeRef
    manager: EmployeeRef
    effective_from: date | None
    effective_to: date | None
    reason: str | None
    created_at: datetime


class ReportingOut(BaseModel):
    as_of: date
    managers: list[ReportingRecordOut]
    history: list[ReportingRecordOut]
    direct_reports: list[ReportingRecordOut]


class ManagerSet(BaseModel):
    manager_id: uuid.UUID
    relationship_type_id: uuid.UUID | None = Field(
        default=None, description="Defaults to LINE_MANAGER."
    )
    effective_from: date | None = None
    reason: Reason | None = None


# ---------------------------------------------------------------------- account


class EmployeeAccountOut(BaseModel):
    accounts: list[AccountRef] = Field(description="Linked accounts, including disabled ones.")
    flags: list[str] = Field(description="Mismatches to review; nothing changes automatically.")
    history: list[AuditEventOut] = Field(description="Link and unlink events, newest first.")


class AccountLink(BaseModel):
    user_public_id: uuid.UUID
    reason: Reason | None = None


class AccountUnlink(BaseModel):
    user_public_id: uuid.UUID
    reason: Reason | None = None


# ------------------------------------------------------------------ data quality


class DataQualityOut(BaseModel):
    as_of: date
    counts: dict[str, int]
    check: str | None
    items: list[EmployeeSummary]
    next_cursor: str | None
