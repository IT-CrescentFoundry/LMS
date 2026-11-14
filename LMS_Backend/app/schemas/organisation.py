"""Organisation structure schemas: unit types, units, hierarchy, locations (Stage C1).

Write requests that change an existing record carry its ``version`` (optimistic
locking). PATCH bodies are partial: only the fields sent are changed; sending null
clears an optional field, and is rejected for required ones.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, Field, model_validator

from app.models.common import TranslationLocale

Code = Annotated[str, Field(min_length=1, max_length=50, description="Letters, digits, - and _.")]
Name = Annotated[str, Field(min_length=1, max_length=200)]
ShortText = Annotated[str, Field(max_length=100)]
Reason = Annotated[str, Field(max_length=500)]
Version = Annotated[int, Field(ge=1, description="The version you last read.")]
Translations = Annotated[
    dict[TranslationLocale, Annotated[str, Field(max_length=200)] | None],
    Field(description="Display names by locale; an empty value or null removes a locale."),
]
UnitStatus = Literal["active", "closed", "not_started"]


class PatchModel(BaseModel):
    """Partial update: reject explicit null for fields that cannot be empty."""

    required_if_sent: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _no_null_for_required(self) -> "PatchModel":
        for field in self.required_if_sent:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    def changes(self, *exclude: str) -> dict[str, Any]:
        return self.model_dump(
            exclude_unset=True, exclude={"version", "reason", "translations", *exclude}
        )


class RefOut(BaseModel):
    """A compact reference to another record."""

    public_id: uuid.UUID
    code: str
    name: str


class WarningOut(BaseModel):
    code: str
    message: str


class Tracked(BaseModel):
    version: int
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------------- unit types


class OrgUnitTypeOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    sort_order: int
    allows_employee_assignment: bool
    is_active: bool
    parent_rule_mode: Literal["advisory", "strict"]
    allow_root: bool = Field(description="True when a rule allows this type as a root.")
    allowed_parent_types: list[RefOut] = Field(
        description="Empty together with allow_root=false means no rules (anything allowed)."
    )
    translations: dict[str, str]


class OrgUnitTypeCreate(BaseModel):
    code: Code
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: Annotated[str, Field(max_length=500)] | None = None
    sort_order: Annotated[int, Field(ge=0, le=100000)] = 0
    allows_employee_assignment: bool = True
    parent_rule_mode: Literal["advisory", "strict"] = "advisory"
    translations: Translations = Field(default_factory=dict)


class OrgUnitTypeUpdate(PatchModel):
    required_if_sent = (
        "name",
        "sort_order",
        "allows_employee_assignment",
        "is_active",
        "parent_rule_mode",
    )

    version: Version
    name: Annotated[str, Field(min_length=1, max_length=150)] | None = None
    description: Annotated[str, Field(max_length=500)] | None = None
    sort_order: Annotated[int, Field(ge=0, le=100000)] | None = None
    allows_employee_assignment: bool | None = None
    is_active: bool | None = None
    parent_rule_mode: Literal["advisory", "strict"] | None = None
    translations: Translations | None = None


class ParentRulesUpdate(BaseModel):
    version: Version
    allow_root: bool
    parent_type_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)


# ------------------------------------------------------------------------------ units


class OrgUnitOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    unit_type: RefOut
    location: RefOut | None
    as_of: date = Field(description="Date for which parent, path and status are shown.")
    parent: RefOut | None
    path: list[RefOut] = Field(description="Ancestors from the root down to the parent.")
    status: UnitStatus
    effective_from: date | None = Field(description="Null means the start was not recorded.")
    effective_to: date | None = Field(description="Closure date (exclusive); null if open.")
    external_ref: str | None
    translations: dict[str, str]


class OrgUnitWriteOut(BaseModel):
    unit: OrgUnitOut
    warnings: list[WarningOut] = Field(
        default_factory=list, description="Non-blocking findings, e.g. advisory type rules."
    )


class OrgUnitCreate(BaseModel):
    code: Code
    name: Name
    short_name: Annotated[str, Field(max_length=50)] | None = None
    unit_type_id: uuid.UUID
    location_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = Field(default=None, description="Null creates a root unit.")
    effective_from: date | None = Field(
        default=None, description="Start date; null when it is not recorded."
    )
    external_ref: ShortText | None = None
    translations: Translations = Field(default_factory=dict)


class OrgUnitCorrect(PatchModel):
    """Correct wrongly recorded data. Use move/close for real organisational changes."""

    required_if_sent = ("code", "name", "unit_type_id")

    version: Version
    reason: Reason | None = None
    code: Code | None = None
    name: Name | None = None
    short_name: Annotated[str, Field(max_length=50)] | None = None
    unit_type_id: uuid.UUID | None = None
    location_id: uuid.UUID | None = None
    effective_from: date | None = None
    external_ref: ShortText | None = None
    translations: Translations | None = None


class OrgUnitMove(BaseModel):
    version: Version
    new_parent_id: uuid.UUID | None = Field(description="Null makes the unit a root.")
    effective_date: date = Field(description="First day under the new parent.")


class OrgUnitClose(BaseModel):
    version: Version
    effective_date: date = Field(description="First day on which the unit no longer exists.")
    reason: Reason | None = None


class OrgUnitReopen(BaseModel):
    version: Version
    reason: Reason | None = None


class OrgTreeNode(BaseModel):
    public_id: uuid.UUID
    code: str
    name: str
    short_name: str | None
    unit_type: RefOut
    location: RefOut | None
    parent_id: uuid.UUID | None = Field(description="public_id of the parent on as_of.")
    status: UnitStatus
    translations: dict[str, str]


class OrgTreeOut(BaseModel):
    as_of: date
    nodes: list[OrgTreeNode] = Field(description="Flat list ordered by code; build the tree.")


class HierarchyLinkOut(BaseModel):
    parent: RefOut
    effective_from: date | None
    effective_to: date | None
    recorded_at: datetime
    ended_at: datetime | None


class UnitHistoryOut(BaseModel):
    unit: RefOut
    effective_from: date | None
    effective_to: date | None
    placements: list[HierarchyLinkOut] = Field(
        description="Parent links, oldest first; periods without a link are root periods."
    )


# -------------------------------------------------------------------------- locations


class LocationFields(BaseModel):
    address_line1: Annotated[str, Field(max_length=200)] | None = None
    address_line2: Annotated[str, Field(max_length=200)] | None = None
    city: ShortText | None = None
    state: ShortText | None = None
    postal_code: Annotated[str, Field(max_length=20)] | None = None
    country_code: Annotated[str, Field(pattern=r"^[A-Za-z]{2}$")] | None = None
    time_zone: Annotated[str, Field(max_length=64)] | None = None


class LocationOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    address_line1: str | None
    address_line2: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    country_code: str | None
    time_zone: str | None
    is_active: bool


class LocationCreate(LocationFields):
    code: Code
    name: Name


class LocationUpdate(LocationFields, PatchModel):
    required_if_sent = ("code", "name", "is_active")

    version: Version
    code: Code | None = None
    name: Name | None = None
    is_active: bool | None = None
