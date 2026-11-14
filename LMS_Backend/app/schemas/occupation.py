"""Occupational reference schemas (Stage C1): job families, grades, levels,
designations, functional roles and their mappings, responsibilities.

None of these records grant LMS permissions or practical authorisation.
"""

import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.organisation import (
    Code,
    Name,
    PatchModel,
    Reason,
    RefOut,
    Tracked,
    Translations,
    Version,
)

Description = Annotated[str, Field(max_length=1000)]
Rank = Annotated[int, Field(ge=0, le=100000, description="Optional ordering; no meaning implied.")]


# ------------------------------------------------------------------------ job families


class JobFamilyOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    parent: RefOut | None
    is_active: bool


class JobFamilyCreate(BaseModel):
    code: Code
    name: Name
    description: Annotated[str, Field(max_length=500)] | None = None
    parent_id: uuid.UUID | None = None


class JobFamilyUpdate(PatchModel):
    required_if_sent = ("code", "name", "is_active")

    version: Version
    code: Code | None = None
    name: Name | None = None
    description: Annotated[str, Field(max_length=500)] | None = None
    parent_id: uuid.UUID | None = None
    is_active: bool | None = None


# -------------------------------------------------------------------- grades and levels


class RankedOut(Tracked):
    """A grade or a level. The two lists are independent (Q-45)."""

    public_id: uuid.UUID
    code: str
    name: str
    rank: int | None
    is_active: bool


class RankedCreate(BaseModel):
    code: Code
    name: Annotated[str, Field(min_length=1, max_length=100)]
    rank: Rank | None = None


class RankedUpdate(PatchModel):
    required_if_sent = ("code", "name", "is_active")

    version: Version
    code: Code | None = None
    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    rank: Rank | None = None
    is_active: bool | None = None


# ------------------------------------------------------------------------ designations


class DesignationOut(Tracked):
    public_id: uuid.UUID
    code: str
    title: str
    job_family: RefOut | None
    is_active: bool
    translations: dict[str, str]


class DesignationCreate(BaseModel):
    code: Code
    title: Name
    job_family_id: uuid.UUID | None = None
    translations: Translations = Field(default_factory=dict)


class DesignationUpdate(PatchModel):
    required_if_sent = ("code", "title", "is_active")

    version: Version
    code: Code | None = None
    title: Name | None = None
    job_family_id: uuid.UUID | None = None
    is_active: bool | None = None
    translations: Translations | None = None


# -------------------------------------------------------------------- functional roles


class FunctionalRoleOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    job_family: RefOut | None
    owner_unit: RefOut | None
    is_active: bool
    translations: dict[str, str]


class FunctionalRoleCreate(BaseModel):
    code: Code
    name: Name
    description: Description | None = None
    job_family_id: uuid.UUID | None = None
    owner_unit_id: uuid.UUID | None = None
    translations: Translations = Field(default_factory=dict)


class FunctionalRoleUpdate(PatchModel):
    required_if_sent = ("code", "name", "is_active")

    version: Version
    code: Code | None = None
    name: Name | None = None
    description: Description | None = None
    job_family_id: uuid.UUID | None = None
    owner_unit_id: uuid.UUID | None = None
    is_active: bool | None = None
    translations: Translations | None = None


class DesignationRoleMappingOut(BaseModel):
    public_id: uuid.UUID
    designation: RefOut
    functional_role: RefOut
    scope_unit: RefOut | None = Field(description="Null means the mapping applies everywhere.")
    include_descendants: bool
    effective_from: date | None
    effective_to: date | None
    created_at: datetime
    ended_at: datetime | None


class DesignationRoleMappingCreate(BaseModel):
    functional_role_id: uuid.UUID
    scope_unit_id: uuid.UUID | None = None
    include_descendants: bool = True
    effective_from: date | None = Field(
        default=None, description="Defaults to today (business date)."
    )


class DesignationRoleMappingEnd(BaseModel):
    effective_to: date = Field(description="First day on which the mapping no longer applies.")
    reason: Reason | None = None


# -------------------------------------------------------------------- responsibilities


class ResponsibilityOut(Tracked):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    category: str | None
    is_active: bool
    translations: dict[str, str]


class ResponsibilityCreate(BaseModel):
    code: Code
    name: Name
    description: Description | None = None
    category: Annotated[str, Field(max_length=50)] | None = None
    translations: Translations = Field(default_factory=dict)


class ResponsibilityUpdate(PatchModel):
    required_if_sent = ("code", "name", "is_active")

    version: Version
    code: Code | None = None
    name: Name | None = None
    description: Description | None = None
    category: Annotated[str, Field(max_length=50)] | None = None
    is_active: bool | None = None
    translations: Translations | None = None
