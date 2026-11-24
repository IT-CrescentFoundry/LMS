"""Import profiles (Stage D): code-defined, versioned and immutable.

A profile version never changes meaning once released: a change of fields, aliases or
rules is a new version, and every import job records the version it was validated
with. Header aliases are matched only after deterministic normalisation (case,
spacing, punctuation) - there is no fuzzy header matching.

Profile ``employees`` v1 (import profile 1, scoped to the C3 employee master):

* section ``employees``   - employee records (create; listed corrections on approval);
* section ``assignments`` - effective-dated assignments (create only, never rewrite);
* section ``reporting``   - line-manager relationships (create only).

A worksheet may be mapped as more than one section (a flat HR export that holds
employee, department and manager columns in one row). Organisation units,
designations, locations, grades and levels are only *referenced*: they are never
created by an import (Q-47, Q-53).
"""

import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum


class FieldType(StrEnum):
    EMPLOYEE_CODE = "employee_code"
    TEXT = "text"
    EMAIL = "email"
    DATE = "date"
    STATUS = "status"
    LANGUAGE = "language"
    ASSIGNMENT_TYPE = "assignment_type"
    REFERENCE = "reference"


class ReferenceKind(StrEnum):
    ORG_UNIT = "org_unit"
    DESIGNATION = "designation"
    LOCATION = "location"
    GRADE = "grade"
    JOB_LEVEL = "job_level"


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: FieldType
    required: bool = False
    aliases: tuple[str, ...] = ()
    max_length: int | None = None
    reference: ReferenceKind | None = None


@dataclass(frozen=True)
class SectionSpec:
    kind: str
    sheet_aliases: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    natural_key: tuple[str, ...]

    def field(self, name: str) -> FieldSpec:
        return next(item for item in self.fields if item.name == name)

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.fields)


@dataclass(frozen=True)
class ProfileSpec:
    code: str
    version: int
    sections: tuple[SectionSpec, ...]
    commit_order: tuple[str, ...]
    # Commit semantics: all-or-nothing for the rows not explicitly skipped.
    commit_mode: str = "all_or_nothing_with_explicit_skips"
    header_search_rows: int = 10
    options: dict[str, str] = field(default_factory=dict)

    def section(self, kind: str) -> SectionSpec:
        return next(item for item in self.sections if item.kind == kind)


def normalise_label(text: str) -> str:
    """Deterministic comparison form of a header or label (never fuzzy)."""
    value = unicodedata.normalize("NFKC", text).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[\s_]+", " ", value)
    value = re.sub(r"[.,:;()\[\]#*]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


# --- protected exclusion list (EXCEL_IMPORT_PROFILES §4.2) ------------------------------------
# Headers matching these patterns can never be mapped; their cell values are never read.
EXCLUDED_HEADER_PATTERNS: tuple[str, ...] = (
    r"\bctc\b",
    r"salary",
    r"\bgross\b",
    r"net pay",
    r"\bbasic\b",
    r"\bhra\b",
    r"allowance",
    r"\bwage",
    r"compensation",
    r"increment",
    r"\bbonus",
    r"\bbank\b",
    r"account (no|number)",
    r"\bifsc\b",
    r"\bpan\b",
    r"aadha?ar",
    r"\buan\b",
    r"\bpf (no|number)\b",
    r"\besi\b",
    r"date of birth",
    r"\bdob\b",
    r"birth ?day",
    r"\bgender\b",
    r"\bsex\b",
    r"(?<!email )(?<!e mail )address",  # postal/home address; "email address" is allowed
    r"mobile",
    r"phone",
    r"contact (no|number)",
    r"personal (e ?mail|email)",
    r"blood",
    r"marital",
    r"\bfather",
    r"\bmother",
    r"spouse",
    r"religion",
    r"\bcaste\b",
    r"medical",
    r"health",
    r"emergency",
)
_EXCLUDED = tuple(re.compile(pattern) for pattern in EXCLUDED_HEADER_PATTERNS)


def is_excluded_header(header: str) -> bool:
    label = normalise_label(header)
    return any(pattern.search(label) for pattern in _EXCLUDED)


# --- profile: employees v1 -------------------------------------------------------------------
_CODE_ALIASES = (
    "Employee Code",
    "Emp Code",
    "Emp. Code",
    "Employee No",
    "Employee Number",
    "Emp No",
    "Employee ID",
    "Emp ID",
    "Staff Code",
)

EMPLOYEES_V1 = ProfileSpec(
    code="employees",
    version=1,
    commit_order=("employees", "assignments", "reporting"),
    sections=(
        SectionSpec(
            kind="employees",
            sheet_aliases=("Employees", "Employee", "Employee Master", "Employee List"),
            natural_key=("employee_code",),
            fields=(
                FieldSpec("employee_code", FieldType.EMPLOYEE_CODE, True, _CODE_ALIASES, 30),
                FieldSpec(
                    "full_name",
                    FieldType.TEXT,
                    True,
                    ("Full Name", "Employee Name", "Name", "Emp Name"),
                    200,
                ),
                FieldSpec("display_name", FieldType.TEXT, False, ("Display Name", "Known As"), 200),
                FieldSpec(
                    "preferred_language",
                    FieldType.LANGUAGE,
                    False,
                    ("Preferred Language", "Language"),
                ),
                FieldSpec(
                    "work_email",
                    FieldType.EMAIL,
                    False,
                    ("Work Email", "Official Email", "Office Email", "Email ID Official"),
                    254,
                ),
                FieldSpec(
                    "employment_status",
                    FieldType.STATUS,
                    False,
                    ("Employment Status", "Status", "Emp Status"),
                ),
                FieldSpec(
                    "date_of_joining",
                    FieldType.DATE,
                    False,
                    ("Date of Joining", "DOJ", "Joining Date"),
                ),
                FieldSpec(
                    "last_working_day",
                    FieldType.DATE,
                    False,
                    ("Last Working Day", "Date of Separation", "Separation Date"),
                ),
                FieldSpec(
                    "external_ref",
                    FieldType.TEXT,
                    False,
                    ("External Reference", "HRMS ID", "Reference"),
                    100,
                ),
            ),
        ),
        SectionSpec(
            kind="assignments",
            sheet_aliases=("Assignments", "Assignment"),
            natural_key=("employee_code", "unit", "assignment_type", "effective_from"),
            fields=(
                FieldSpec("employee_code", FieldType.EMPLOYEE_CODE, True, _CODE_ALIASES, 30),
                FieldSpec(
                    "assignment_type", FieldType.ASSIGNMENT_TYPE, False, ("Assignment Type", "Type")
                ),
                FieldSpec(
                    "unit",
                    FieldType.REFERENCE,
                    True,
                    (
                        "Organisation Unit",
                        "Organization Unit",
                        "Unit",
                        "Unit Code",
                        "Department",
                        "Function",
                        "Sub-function",
                        "Section",
                    ),
                    200,
                    ReferenceKind.ORG_UNIT,
                ),
                FieldSpec(
                    "designation",
                    FieldType.REFERENCE,
                    False,
                    ("Designation",),
                    200,
                    ReferenceKind.DESIGNATION,
                ),
                FieldSpec(
                    "grade", FieldType.REFERENCE, False, ("Grade",), 200, ReferenceKind.GRADE
                ),
                FieldSpec(
                    "level",
                    FieldType.REFERENCE,
                    False,
                    ("Level", "Job Level"),
                    200,
                    ReferenceKind.JOB_LEVEL,
                ),
                FieldSpec(
                    "location",
                    FieldType.REFERENCE,
                    False,
                    ("Location", "Plant", "Work Location"),
                    200,
                    ReferenceKind.LOCATION,
                ),
                FieldSpec(
                    "effective_from",
                    FieldType.DATE,
                    True,
                    ("Effective From", "Assignment From", "Start Date", "From"),
                ),
                FieldSpec(
                    "last_day",
                    FieldType.DATE,
                    False,
                    ("Last Day in Effect", "Last Day", "End Date", "To"),
                ),
            ),
        ),
        SectionSpec(
            kind="reporting",
            sheet_aliases=("Reporting", "Reporting Lines", "Managers"),
            natural_key=("employee_code", "effective_from"),
            fields=(
                FieldSpec("employee_code", FieldType.EMPLOYEE_CODE, True, _CODE_ALIASES, 30),
                FieldSpec(
                    "manager_code",
                    FieldType.EMPLOYEE_CODE,
                    True,
                    (
                        "Manager Code",
                        "Line Manager Code",
                        "Reporting Manager Code",
                        "Reports To Code",
                    ),
                    30,
                ),
                FieldSpec(
                    "effective_from",
                    FieldType.DATE,
                    True,
                    ("Effective From", "Reporting From", "Manager From", "From"),
                ),
            ),
        ),
    ),
    options={"date_order": "DMY"},
)

# Profile ``organisation`` v1 (first release; closes the unit part of Q-47): new
# organisation units with their type, parent and location. New codes are created; a row
# whose code already exists is compared and either unchanged or a listed UPDATE that is
# applied only when the approver explicitly approves updates (rename/type/location as
# audited corrections, new parent as an effective-dated move). Never closes or deletes a
# unit. Parents may be existing units or units earlier in the file.
ORGANISATION_V1 = ProfileSpec(
    code="organisation",
    version=1,
    commit_order=("units",),
    sections=(
        SectionSpec(
            kind="units",
            sheet_aliases=("Organisation Units", "Org Units", "Units", "Organisation Structure"),
            natural_key=("unit_code",),
            fields=(
                FieldSpec(
                    "unit_code", FieldType.TEXT, True, ("Unit Code", "Org Unit Code", "Code"), 50
                ),
                FieldSpec("unit_name", FieldType.TEXT, True, ("Unit Name", "Name"), 200),
                FieldSpec(
                    "unit_type",
                    FieldType.TEXT,
                    True,
                    ("Unit Type", "Unit Type Code", "Type"),
                    150,
                ),
                FieldSpec(
                    "parent_code",
                    FieldType.TEXT,
                    False,
                    ("Parent Unit Code", "Parent Code", "Parent"),
                    50,
                ),
                FieldSpec("location", FieldType.TEXT, False, ("Location Code", "Location"), 200),
                FieldSpec("short_name", FieldType.TEXT, False, ("Short Name",), 50),
                FieldSpec(
                    "effective_from",
                    FieldType.DATE,
                    False,
                    ("Effective From", "Start Date", "From"),
                ),
                FieldSpec(
                    "external_ref",
                    FieldType.TEXT,
                    False,
                    ("External Reference", "HRMS ID", "External Ref"),
                    100,
                ),
            ),
        ),
    ),
    options={"date_order": "DMY"},
)

PROFILES: dict[tuple[str, int], ProfileSpec] = {
    (EMPLOYEES_V1.code, EMPLOYEES_V1.version): EMPLOYEES_V1,
    (ORGANISATION_V1.code, ORGANISATION_V1.version): ORGANISATION_V1,
}
CURRENT_VERSION: dict[str, int] = {"employees": 1, "organisation": 1}


def get_profile(code: str, version: int | None = None) -> ProfileSpec | None:
    resolved = CURRENT_VERSION.get(code) if version is None else version
    return None if resolved is None else PROFILES.get((code, resolved))


def suggest_field(section: SectionSpec, header: str) -> str | None:
    """Field whose alias equals the normalised header (exact match only)."""
    label = normalise_label(header)
    if not label or is_excluded_header(header):
        return None
    for spec in section.fields:
        if label == normalise_label(spec.name.replace("_", " ")) or any(
            label == normalise_label(alias) for alias in spec.aliases
        ):
            return spec.name
    return None


def suggest_section(sheet_name: str, profile: ProfileSpec) -> str | None:
    label = normalise_label(sheet_name)
    for section in profile.sections:
        if any(label == normalise_label(alias) for alias in section.sheet_aliases):
            return section.kind
    return None
