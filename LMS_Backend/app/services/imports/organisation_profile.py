"""Import profile ``organisation`` v1: validation and domain execution.

Runs inside the generic import job (upload -> mapping -> dry-run validation -> explicit
approval -> one-transaction commit with provenance). Every new unit is created through
``units.create_unit``, so the same rules as the screens apply: unique codes, sibling
name uniqueness, parent-type rules (advisory warnings or strict errors), active unit
types and locations, and the hierarchy lock.

Row classification:

* ``new``       - the code does not exist; the unit is created (parents first);
* ``unchanged`` - the code exists and every supplied value matches;
* ``update``    - the code exists and supplied values differ. The preview lists each
  difference (``from``/``to``; a parent change also shows its effective date). The
  update is applied ONLY when the approver explicitly chooses "apply listed updates"
  at commit; otherwise the row is skipped and the unit stays as it is. Renames, type,
  location, short-name and external-reference changes are audited corrections
  (``correct_unit``); a new parent is an effective-dated move (``move_unit``) from the
  commit's business date, so the previous placement stays in the history. Blank
  optional cells never clear recorded values; start dates are never changed; units are
  never closed or deleted by an import (closing is done on the Organisation screens);
* ``error``     - unknown type/location, missing parent, duplicate code in the file,
  a parent cycle inside the file, or a domain rule refused the change.
"""

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import select

from app.models.imports import IssueSeverity, RowOutcome
from app.models.organisation import Location, OrgUnit, OrgUnitType
from app.services.imports.employees_profile import DomainContext, StagedRow, _savepoint
from app.services.imports.profiles import normalise_label
from app.services.organisation import units as unit_service
from app.services.organisation.unit_types import OrgWarning


def check_within_file(rows: list[StagedRow]) -> None:
    by_code: dict[str, list[StagedRow]] = defaultdict(list)
    for row in rows:
        code = row.values.get("unit_code")
        if not row.skipped and isinstance(code, str):
            by_code[code.strip().upper()].append(row)
    for group in by_code.values():
        if len(group) > 1:
            for row in group:
                others = [f"{o.sheet}!{o.row_number}" for o in group if o is not row]
                row.add("duplicate_in_file", "unit_code", rows=others[:5])


def _type_index(ctx: DomainContext) -> dict[str, OrgUnitType]:
    index: dict[str, OrgUnitType] = {}
    for unit_type in ctx.db.scalars(select(OrgUnitType)):
        index[normalise_label(unit_type.code)] = unit_type
        index.setdefault(normalise_label(unit_type.name), unit_type)
    return index


def _location_index(ctx: DomainContext) -> dict[str, Location]:
    index: dict[str, Location] = {}
    for location in ctx.db.scalars(select(Location)):
        index[normalise_label(location.code)] = location
        index.setdefault(normalise_label(location.name), location)
    return index


def _order(rows: list[StagedRow], existing: set[str]) -> tuple[list[StagedRow], list[StagedRow]]:
    """Parents before children. Returns (ordered, unresolvable)."""
    pending = list(rows)
    known = set(existing)
    ordered: list[StagedRow] = []
    progress = True
    while pending and progress:
        progress = False
        for row in list(pending):
            parent = row.values.get("parent_code")
            if not parent or str(parent).strip().upper() in known:
                ordered.append(row)
                known.add(str(row.values["unit_code"]).strip().upper())
                pending.remove(row)
                progress = True
    return ordered, pending


def _existing_unit_row(
    ctx: DomainContext,
    row: StagedRow,
    current: OrgUnit,
    parents: dict[int, int],
    unit_type: OrgUnitType,
    location: Location | None,
    parent: OrgUnit | None,
    parent_code: str | None,
    today: date,
) -> None:
    """Compare an existing unit with its row; list differences as a proposed update.

    Blank optional cells never clear a recorded value (removing a parent or location
    is done on the Organisation screens). The start date is never changed by an
    import. Corrections (name, type, location, short name, external reference) use
    ``correct_unit``; a different parent is an effective-dated ``move_unit`` from the
    commit's business date. Nothing is written unless the approver explicitly chose to
    apply the listed updates."""
    values = row.values
    current_parent_id = parents.get(current.id)
    current_parent = ctx.db.get(OrgUnit, current_parent_id) if current_parent_id else None
    changes: dict[str, Any] = {}
    corrections: dict[str, object] = {}

    name = str(values["unit_name"]).strip()
    if name != current.name:
        changes["unit_name"] = {"from": current.name, "to": name}
        corrections["name"] = name
    if unit_type.id != current.unit_type_id:
        changes["unit_type"] = {"from": current.unit_type.code, "to": unit_type.code}
        corrections["unit_type_id"] = unit_type.public_id
    if location is not None and location.id != current.location_id:
        before = current.location.code if current.location else None
        changes["location"] = {"from": before, "to": location.code}
        corrections["location_id"] = location.public_id
    for field in ("short_name", "external_ref"):
        new_value = values.get(field)
        if new_value and str(new_value).strip() != (getattr(current, field) or ""):
            changes[field] = {"from": getattr(current, field), "to": str(new_value).strip()}
            corrections[field] = str(new_value).strip()
    move = parent is not None and parent.id != current_parent_id
    if move:
        changes["parent_code"] = {
            "from": current_parent.code if current_parent else None,
            "to": parent.code if parent else parent_code,
            "effective_date": today.isoformat(),
        }

    if not changes:
        row.outcome = RowOutcome.UNCHANGED
        return
    row.outcome = RowOutcome.UPDATE
    row.changes = changes
    if ctx.commit and not ctx.apply_updates:
        return  # listed updates not approved: the unit stays unchanged (counted as skipped)

    def apply() -> tuple[OrgUnit, list[OrgWarning]]:
        warnings: list[OrgWarning] = []
        unit = current
        if corrections:
            unit, found = unit_service.correct_unit(
                ctx.db,
                current.public_id,
                actor=ctx.actor,
                meta=ctx.meta,
                version=current.version,
                reason=f"Excel import {ctx.job_public_id}",
                changes=corrections,
            )
            warnings.extend(found)
        if move and parent is not None:
            unit, found = unit_service.move_unit(
                ctx.db,
                current.public_id,
                actor=ctx.actor,
                meta=ctx.meta,
                version=unit.version,
                new_parent_id=parent.public_id,
                effective_date=today,
            )
            warnings.extend(found)
        return unit, warnings

    result = _savepoint(ctx, row, apply)
    if result is None:
        row.outcome = RowOutcome.ERROR
        return
    for warning in result[1]:
        row.add(warning.code, severity=IssueSeverity.WARNING)


def run_domain(ctx: DomainContext, rows: list[StagedRow], today: date) -> None:
    active = [r for r in rows if not r.skipped and not r.blocked]
    for row in rows:
        if row.skipped:
            row.outcome = RowOutcome.SKIPPED
        elif row.blocked:
            row.outcome = RowOutcome.ERROR
    if not active:
        return
    types = _type_index(ctx)
    locations = _location_index(ctx)
    codes = sorted(
        {str(r.values["unit_code"]).strip().upper() for r in active}
        | {
            str(r.values["parent_code"]).strip().upper()
            for r in active
            if r.values.get("parent_code")
        }
    )
    existing = {u.code: u for u in ctx.db.scalars(select(OrgUnit).where(OrgUnit.code.in_(codes)))}
    parents = unit_service.parents_on(ctx.db, today)
    in_file_codes = {str(r.values["unit_code"]).strip().upper() for r in active}
    ordered, unresolved = _order(active, set(existing))
    for row in unresolved:
        missing = str(row.values["parent_code"]).strip().upper()
        row.add(
            "parent_cycle_in_file" if missing in in_file_codes else "parent_not_found",
            "parent_code",
        )
        row.outcome = RowOutcome.ERROR
    created: dict[str, OrgUnit] = {}
    failed: set[str] = set()
    for row in ordered:
        values = row.values
        code = str(values["unit_code"]).strip().upper()
        unit_type = types.get(normalise_label(str(values["unit_type"])))
        if unit_type is None or not unit_type.is_active:
            row.add("unit_type_unknown", "unit_type")
        location = None
        if values.get("location"):
            location = locations.get(normalise_label(str(values["location"])))
            if location is None or not location.is_active:
                row.add("location_unknown", "location")
        parent_code = (
            str(values["parent_code"]).strip().upper() if values.get("parent_code") else None
        )
        if parent_code and parent_code in failed:
            row.add("parent_row_failed", "parent_code")
        parent = (created.get(parent_code) or existing.get(parent_code)) if parent_code else None
        if row.blocked:
            row.outcome = RowOutcome.ERROR
            failed.add(code)
            continue
        if unit_type is None:  # pragma: no cover - blocked above
            continue
        current = existing.get(code)
        if current is not None:
            row.target_public_id = current.public_id
            _existing_unit_row(
                ctx, row, current, parents, unit_type, location, parent, parent_code, today
            )
            if row.outcome == RowOutcome.ERROR:
                failed.add(code)
            continue

        def create(
            values: dict[str, object] = values,
            code: str = code,
            unit_type: OrgUnitType = unit_type,
            location: Location | None = location,
            parent: OrgUnit | None = parent,
        ) -> object:
            return unit_service.create_unit(
                ctx.db,
                actor=ctx.actor,
                meta=ctx.meta,
                code=code,
                name=str(values["unit_name"]),
                short_name=values.get("short_name"),  # type: ignore[arg-type]
                unit_type_id=unit_type.public_id,
                location_id=location.public_id if location else None,
                parent_id=parent.public_id if parent else None,
                effective_from=values.get("effective_from"),  # type: ignore[arg-type]
                external_ref=values.get("external_ref"),  # type: ignore[arg-type]
                translations={},
            )

        result = _savepoint(ctx, row, create)
        if result is None:
            row.outcome = RowOutcome.ERROR
            failed.add(code)
            continue
        unit, warnings = result
        for warning in warnings:
            row.add(warning.code, severity=IssueSeverity.WARNING)
        created[code] = unit
        row.outcome = RowOutcome.NEW
        row.target_public_id = unit.public_id
