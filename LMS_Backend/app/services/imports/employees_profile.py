"""Profile ``employees`` v1: parse, validate, dry-run and commit (Stage D).

Validation layers (EXCEL_IMPORT_PROFILES §5):

1. file / structure - in ``workbook.py`` and the job service;
2. field - required values, formats, codes, dates, statuses (``normalise.py``);
3. within file - duplicate natural keys, probable duplicate people;
4. references - employees, managers, units, designations, locations, grades, levels;
5. business rules - by calling the **same C3 domain services** the screens use, each
   row in its own SAVEPOINT. Validation runs them inside a transaction that is then
   rolled back (nothing reaches the domain tables); commit runs them again inside one
   transaction that is kept only if every row succeeds.

Existing records are matched by natural keys. Employees: differing *listed* fields are
proposed as corrections (applied only with explicit approval); status changes and
separations are never applied by an import (status workflow). Assignments and reporting
lines are created only - an import never rewrites assignment history.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.employees import (
    LINE_MANAGER,
    AssignmentType,
    Employee,
    EmployeeAssignment,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.models.imports import IssueSeverity, RowDecision, RowOutcome
from app.services.employees import assignments as assignment_service
from app.services.employees import employees as employee_service
from app.services.employees import reporting as reporting_service
from app.services.identity.context import Actor
from app.services.imports import normalise
from app.services.imports.profiles import FieldType, ProfileSpec, SectionSpec, normalise_label
from app.services.imports.references import MODELS, ReferenceIndex
from app.services.imports.workbook import Limits, SourceRow, iter_rows, sheet_flags

# Employee fields an import may propose as corrections (never status or separation).
UPDATABLE_FIELDS = (
    "full_name",
    "display_name",
    "preferred_language",
    "work_email",
    "date_of_joining",
    "external_ref",
)
REFERENCE_FIELD_IDS = {
    "designation": "designation_id",
    "grade": "grade_id",
    "level": "job_level_id",
    "location": "location_id",
}


@dataclass
class IssueDraft:
    code: str
    severity: str = IssueSeverity.ERROR
    field: str | None = None
    column: str | None = None
    source_value: str | None = None
    params: dict[str, Any] | None = None


@dataclass
class StagedRow:
    section: str
    sheet: str
    row_number: int
    values: dict[str, Any]
    source: dict[str, str | None]
    columns: dict[str, str]
    issues: list[IssueDraft] = field(default_factory=list)
    outcome: str = RowOutcome.NEW
    changes: dict[str, Any] | None = None
    decision: str | None = None
    target_public_id: uuid.UUID | None = None
    record_id: int | None = None  # the staged import_row (commit phase)
    # Commit phase: the (outcome, changes) the approver saw in the validated preview.
    approved: tuple[str, dict[str, Any] | None] | None = None

    @property
    def key(self) -> tuple[str, str, int]:
        return (self.section, self.sheet, self.row_number)

    @property
    def blocked(self) -> bool:
        return any(issue.severity == IssueSeverity.ERROR for issue in self.issues)

    @property
    def skipped(self) -> bool:
        return self.decision == RowDecision.SKIP

    def add(
        self,
        code: str,
        field_name: str | None = None,
        *,
        severity: str = IssueSeverity.ERROR,
        **params: Any,
    ) -> None:
        self.issues.append(
            IssueDraft(
                code,
                severity,
                field_name,
                self.columns.get(field_name) if field_name else None,
                self.source.get(field_name) if field_name else None,
                params or None,
            )
        )

    def natural_key(self, spec: SectionSpec) -> str:
        parts = []
        for name in spec.natural_key:
            value = self.values.get(name)
            parts.append(normalise_label(str(value)) if name == "unit" and value else str(value))
        return "|".join(parts)[:400]


@dataclass
class ParseResult:
    rows: list[StagedRow]
    skipped_blank: int = 0
    skipped_repeated_header: int = 0
    file_issues: list[IssueDraft] = field(default_factory=list)


# ------------------------------------------------------------------ 1-2: parse + fields


def _normalise(spec: Any, value: Any, number_format: str | None) -> normalise.Normalised:
    match spec.type:
        case FieldType.EMPLOYEE_CODE:
            return normalise.employee_code(value, number_format)
        case FieldType.TEXT:
            return normalise.text(value, spec.max_length)
        case FieldType.EMAIL:
            return normalise.email(value)
        case FieldType.DATE:
            return normalise.parse_date(value)
        case FieldType.STATUS:
            return normalise.status(value)
        case FieldType.LANGUAGE:
            return normalise.language(value)
        case FieldType.ASSIGNMENT_TYPE:
            return normalise.assignment_type(value)
        case FieldType.REFERENCE:
            return normalise.reference_text(value, spec.max_length)
    raise AssertionError(spec.type)


def parse(
    workbook: Any,
    archive: Any,
    parts: dict[str, str],
    mapping: list[dict[str, Any]],
    profile: ProfileSpec,
    limits: Limits,
) -> ParseResult:
    result = ParseResult(rows=[])
    for section_map in mapping:
        spec = profile.section(section_map["section"])
        worksheet = workbook[section_map["sheet"]]
        header_row = int(section_map["header_row"])
        columns = {int(index): name for index, name in section_map["columns"].items()}
        header_texts = {
            int(index): text for index, text in section_map.get("header_texts", {}).items()
        }
        letters = {name: section_map["letters"][str(index)] for index, name in columns.items()}
        flags = sheet_flags(archive, parts.get(section_map["sheet"], ""))
        for item in iter_rows(worksheet, header_row, columns, header_texts, flags, limits):
            if isinstance(item, str):
                if item.startswith("blank:"):
                    result.skipped_blank += 1
                else:
                    result.skipped_repeated_header += 1
                continue
            if len(result.rows) >= limits.max_total_rows:
                # Synchronous processing (about 25-30 ms per row in the measured volume
                # test) must finish within the browser's request timeout.
                raise AppError(
                    422,
                    "import_too_many_rows",
                    "This import has more rows than can be processed at once. Split the "
                    "workbook into smaller imports.",
                )
            result.rows.append(_stage(spec, section_map["sheet"], item, letters))
    return result


def _stage(spec: SectionSpec, sheet: str, row: SourceRow, letters: dict[str, str]) -> StagedRow:
    staged = StagedRow(spec.kind, sheet, row.number, {}, {}, letters)
    for name, (value, number_format) in row.cells.items():
        staged.source[name] = normalise.source_text(value)
        result = _normalise(spec.field(name), value, number_format)
        if result.issue:
            staged.add(result.issue, name, **result.params)
        elif result.value is not None:
            staged.values[name] = result.value
    for item in spec.fields:
        if (
            item.required
            and item.name not in staged.values
            and not any(i.field == item.name for i in staged.issues)
        ):
            staged.add("required", item.name)
    if (
        spec.kind == "employees"
        and staged.values.get("last_working_day")
        and staged.values.get("employment_status") != "separated"
    ):
        staged.add("last_working_day_requires_separated", "last_working_day")
    if (
        spec.kind == "employees"
        and staged.values.get("employment_status") == "separated"
        and not staged.values.get("last_working_day")
    ):
        staged.add("separated_requires_last_working_day", "last_working_day")
    if spec.kind == "assignments":
        start, last = staged.values.get("effective_from"), staged.values.get("last_day")
        if isinstance(start, date) and isinstance(last, date) and last < start:
            staged.add("last_day_before_start", "last_day")
    if row.hidden:
        staged.add("row_hidden", severity=IssueSeverity.WARNING)
    if row.merged:
        staged.add("row_merged_cells", severity=IssueSeverity.WARNING)
    return staged


# --------------------------------------------------------------------- 3: within file


def check_within_file(
    rows: list[StagedRow],
    profile: ProfileSpec,
    existing: dict[str, Employee],
    people_on_file: list[Employee],
) -> None:
    by_key: dict[tuple[str, str], list[StagedRow]] = defaultdict(list)
    for row in rows:
        if row.skipped:
            continue
        key = row.natural_key(profile.section(row.section))
        if "None" not in key.split("|"):
            by_key[(row.section, key)].append(row)
    for (_section, _key), group in by_key.items():
        if len(group) > 1:
            for row in group:
                others = [
                    f"{other.sheet}!{other.row_number}" for other in group if other is not row
                ]
                row.add("duplicate_in_file", severity=IssueSeverity.ERROR, rows=others[:5])
    # Probable duplicate people: different codes, same normalised name and joining date.
    people: dict[tuple[str, date], list[tuple[str, str]]] = defaultdict(list)
    for employee in people_on_file:
        if employee.date_of_joining:
            people[(normalise_label(employee.full_name), employee.date_of_joining)].append(
                (employee.employee_code, "existing")
            )
    employee_rows = [
        r
        for r in rows
        if r.section == "employees" and not r.skipped and "employee_code" in r.values
    ]
    for row in employee_rows:
        if row.values.get("full_name") and row.values.get("date_of_joining"):
            people[
                (normalise_label(row.values["full_name"]), row.values["date_of_joining"])
            ].append((row.values["employee_code"], f"{row.sheet}!{row.row_number}"))
    for row in employee_rows:
        if row.values["employee_code"] in existing or not row.values.get("date_of_joining"):
            continue
        matches = people.get(
            (normalise_label(row.values.get("full_name", "")), row.values["date_of_joining"]), []
        )
        others = sorted({code for code, _where in matches if code != row.values["employee_code"]})
        if others and row.decision != RowDecision.DISTINCT:
            row.add(
                "probable_duplicate",
                severity=IssueSeverity.WARNING,
                other_codes=others[:5],
                requires_decision=True,
            )


# -------------------------------------------------------------- 4: references + domain


@dataclass
class DomainContext:
    db: Session
    actor: Actor
    meta: RequestMeta
    job_public_id: uuid.UUID
    apply_updates: bool
    commit: bool
    index: ReferenceIndex
    existing: dict[str, Employee]
    created: dict[str, uuid.UUID] = field(default_factory=dict)
    internal_ids: dict[tuple[str, uuid.UUID], int | None] = field(default_factory=dict)


def load_people_by_joining_date(db: Session, rows: list[StagedRow]) -> list[Employee]:
    """Existing employees sharing a joining date with a new row (probable-duplicate check)."""
    dates = {
        row.values["date_of_joining"]
        for row in rows
        if row.section == "employees" and isinstance(row.values.get("date_of_joining"), date)
    }
    if not dates:
        return []
    return list(db.scalars(select(Employee).where(Employee.date_of_joining.in_(sorted(dates)))))


def load_existing(db: Session, rows: list[StagedRow]) -> dict[str, Employee]:
    codes = {
        row.values[name]
        for row in rows
        for name in ("employee_code", "manager_code")
        if isinstance(row.values.get(name), str)
    }
    if not codes:
        return {}
    found = db.scalars(select(Employee).where(Employee.employee_code.in_(sorted(codes))))
    return {employee.employee_code: employee for employee in found}


def resolve_references(rows: list[StagedRow], index: ReferenceIndex, profile: ProfileSpec) -> None:
    section = profile.section("assignments")
    for row in rows:
        if row.section != "assignments" or row.skipped:
            continue
        for spec in section.fields:
            if spec.reference is None or spec.name not in row.values:
                continue
            text = str(row.values[spec.name])
            resolution = index.resolve(spec.reference, text)
            if resolution.public_id is not None:
                row.values[f"{spec.name}_id"] = str(resolution.public_id)
                row.values[f"{spec.name}_method"] = resolution.method
            else:
                row.add(
                    resolution.issue or "reference_unmapped",
                    spec.name,
                    kind=str(spec.reference),
                    suggestions=[s.__dict__ for s in resolution.suggestions],
                )


def _savepoint(ctx: DomainContext, row: StagedRow, action: Any) -> Any:
    try:
        with ctx.db.begin_nested():
            return action()
    except AppError as error:
        # The domain rule's own code (e.g. primary_overlap, reporting_cycle) is recorded.
        detail = error.details[0].location[-1] if error.details else None
        if detail is not None:
            row.add(error.code, detail=str(detail))
        else:
            row.add(error.code)
        return None


def _internal_id(ctx: DomainContext, model: Any, public_id: str | None) -> int | None:
    if public_id is None:
        return None
    key = (model.__tablename__, uuid.UUID(public_id))
    if key not in ctx.internal_ids:
        ctx.internal_ids[key] = ctx.db.scalar(select(model.id).where(model.public_id == key[1]))
    return ctx.internal_ids[key]


def _employee_public_id(ctx: DomainContext, code: str) -> uuid.UUID | None:
    if code in ctx.created:
        return ctx.created[code]
    employee = ctx.existing.get(code)
    return employee.public_id if employee else None


def run_domain(ctx: DomainContext, rows: list[StagedRow], profile: ProfileSpec) -> None:
    """Classify rows and execute the domain services (savepoint per row)."""
    by_section: dict[str, list[StagedRow]] = defaultdict(list)
    for row in rows:
        by_section[row.section].append(row)
    invalid_codes = {
        row.values["employee_code"]
        for row in by_section["employees"]
        if (row.blocked or row.skipped) and "employee_code" in row.values
    }
    for section in profile.commit_order:
        for row in by_section[section]:
            if row.skipped:
                row.outcome = RowOutcome.SKIPPED
                continue
            if row.blocked:
                row.outcome = RowOutcome.ERROR
                continue
            {
                "employees": _employee_row,
                "assignments": _assignment_row,
                "reporting": _reporting_row,
            }[section](ctx, row, invalid_codes)
            if row.blocked:
                row.outcome = RowOutcome.ERROR


def _employee_row(ctx: DomainContext, row: StagedRow, _invalid: set[str]) -> None:
    values = row.values
    code = values["employee_code"]
    current = ctx.existing.get(code)
    if current is None:
        payload = {
            "employee_code": code,
            "full_name": values["full_name"],
            "display_name": values.get("display_name"),
            "preferred_language": values.get("preferred_language"),
            "work_email": values.get("work_email"),
            "employment_status": values.get("employment_status"),
            "date_of_joining": values.get("date_of_joining"),
            "date_of_separation": values.get("last_working_day"),
            "external_ref": values.get("external_ref"),
        }
        created = _savepoint(
            ctx,
            row,
            lambda: employee_service.create_employee(
                ctx.db, actor=ctx.actor, meta=ctx.meta, values=payload
            ),
        )
        if created is not None:
            row.outcome = RowOutcome.NEW
            row.target_public_id = created.public_id
            ctx.created[code] = created.public_id
        return
    row.target_public_id = current.public_id
    if values.get("employment_status") and values["employment_status"] != current.employment_status:
        row.add(
            "status_change_not_applied",
            "employment_status",
            severity=IssueSeverity.WARNING,
            current=current.employment_status,
        )
    if values.get("last_working_day") and values["last_working_day"] != current.date_of_separation:
        row.add("separation_not_applied", "last_working_day", severity=IssueSeverity.WARNING)
    changes = {
        name: {"from": _plain(getattr(current, name)), "to": _plain(values[name])}
        for name in UPDATABLE_FIELDS
        if name in values and values[name] != getattr(current, name)
    }
    if not changes:
        row.outcome = RowOutcome.UNCHANGED
        return
    row.outcome = RowOutcome.UPDATE
    row.changes = changes
    if ctx.commit and not ctx.apply_updates:
        return  # listed corrections not approved: the record stays unchanged (counted as skipped)
    _savepoint(
        ctx,
        row,
        lambda: employee_service.correct_employee(
            ctx.db,
            current.public_id,
            actor=ctx.actor,
            meta=ctx.meta,
            version=current.version,
            reason=f"Import {ctx.job_public_id} ({row.sheet} row {row.row_number})",
            changes={name: values[name] for name in changes},
        ),
    )


def _plain(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value


def _assignment_row(ctx: DomainContext, row: StagedRow, invalid: set[str]) -> None:
    values = row.values
    code = values["employee_code"]
    employee_id = _employee_public_id(ctx, code)
    if employee_id is None:
        row.add(
            "depends_on_invalid_row" if code in invalid else "employee_not_found", "employee_code"
        )
        return
    start: date = values["effective_from"]
    end = values["last_day"] + timedelta(days=1) if values.get("last_day") else None
    unit_id = _internal_id(ctx, MODELS["org_unit"], values.get("unit_id"))
    references = {
        column: _internal_id(
            ctx,
            MODELS[
                {
                    "designation": "designation",
                    "grade": "grade",
                    "level": "job_level",
                    "location": "location",
                }[name]
            ],
            values.get(f"{name}_id"),
        )
        for name, column in REFERENCE_FIELD_IDS.items()
    }
    employee = ctx.existing.get(code)
    if employee is not None:
        same_key = ctx.db.scalars(
            select(EmployeeAssignment).where(
                EmployeeAssignment.employee_id == employee.id,
                EmployeeAssignment.org_unit_id == unit_id,
                EmployeeAssignment.assignment_type == values["assignment_type"],
                EmployeeAssignment.effective_from == start,
            )
        ).first()
        if same_key is not None:
            row.target_public_id = same_key.public_id
            identical = same_key.effective_to == end and all(
                getattr(same_key, column) == references[column] for column in references
            )
            if identical:
                row.outcome = RowOutcome.UNCHANGED
            else:
                row.add("assignment_conflicts_existing")
            return
    raw: dict[str, Any] = {"org_unit_id": uuid.UUID(values["unit_id"])}
    for name, column in REFERENCE_FIELD_IDS.items():
        if values.get(f"{name}_id"):
            raw[column] = uuid.UUID(values[f"{name}_id"])
    result = _savepoint(
        ctx,
        row,
        lambda: assignment_service.create_assignment(
            ctx.db,
            employee_id,
            actor=ctx.actor,
            meta=ctx.meta,
            assignment_type=AssignmentType(values["assignment_type"]),
            raw=raw,
            effective_from=start,
            effective_to=end,
            reason=f"Import {ctx.job_public_id} ({row.sheet} row {row.row_number})",
        ),
    )
    if result is not None:
        assignment, warnings = result
        row.outcome = RowOutcome.NEW
        row.target_public_id = assignment.public_id
        for warning in warnings:
            row.add(warning.code, "unit", severity=IssueSeverity.WARNING)


def _reporting_row(ctx: DomainContext, row: StagedRow, invalid: set[str]) -> None:
    values = row.values
    employee_id = _employee_public_id(ctx, values["employee_code"])
    manager_id = _employee_public_id(ctx, values["manager_code"])
    if employee_id is None:
        row.add(
            "depends_on_invalid_row"
            if values["employee_code"] in invalid
            else "employee_not_found",
            "employee_code",
        )
    if manager_id is None:
        row.add(
            "depends_on_invalid_row" if values["manager_code"] in invalid else "manager_not_found",
            "manager_code",
        )
    if employee_id is None or manager_id is None:
        return
    employee = ctx.existing.get(values["employee_code"])
    manager = ctx.existing.get(values["manager_code"])
    if employee is not None:
        existing = ctx.db.scalars(
            select(ReportingRelationship)
            .join(
                ReportingRelationshipType,
                ReportingRelationshipType.id == ReportingRelationship.relationship_type_id,
            )
            .where(
                ReportingRelationship.employee_id == employee.id,
                ReportingRelationshipType.code == LINE_MANAGER,
                ReportingRelationship.effective_from == values["effective_from"],
            )
        ).first()
        if existing is not None:
            row.target_public_id = existing.public_id
            if manager is not None and existing.manager_employee_id == manager.id:
                row.outcome = RowOutcome.UNCHANGED
            else:
                row.add("reporting_conflicts_existing", "manager_code")
            return
    created = _savepoint(
        ctx,
        row,
        lambda: reporting_service.set_manager(
            ctx.db,
            employee_id,
            actor=ctx.actor,
            meta=ctx.meta,
            manager_id=manager_id,
            relationship_type_id=None,
            effective_from=values["effective_from"],
            reason=f"Import {ctx.job_public_id} ({row.sheet} row {row.row_number})",
        ),
    )
    if created is not None:
        row.outcome = RowOutcome.NEW
        row.target_public_id = created.public_id
