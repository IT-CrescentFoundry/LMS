"""Convert organisation and occupational ORM objects into response schemas."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.occupation import (
    Designation,
    DesignationFunctionalRole,
    FunctionalRole,
    Grade,
    JobFamily,
    JobLevel,
    Responsibility,
)
from app.models.organisation import (
    Location,
    OrgUnit,
    OrgUnitHierarchy,
    OrgUnitType,
    OrgUnitTypeRule,
)
from app.schemas.occupation import (
    DesignationOut,
    DesignationRoleMappingOut,
    FunctionalRoleOut,
    JobFamilyOut,
    RankedOut,
    ResponsibilityOut,
)
from app.schemas.organisation import (
    HierarchyLinkOut,
    LocationOut,
    OrgTreeNode,
    OrgTreeOut,
    OrgUnitOut,
    OrgUnitTypeOut,
    OrgUnitWriteOut,
    RefOut,
    UnitHistoryOut,
    UnitStatus,
    WarningOut,
)
from app.services.organisation.graph import ancestor_path
from app.services.organisation.support import translations_of
from app.services.organisation.unit_types import OrgWarning, all_rules
from app.services.organisation.units import parents_on

# ------------------------------------------------------------------------------ refs


def ref(entity: OrgUnit | OrgUnitType | Location | JobFamily | FunctionalRole) -> RefOut:
    return RefOut(public_id=entity.public_id, code=entity.code, name=entity.name)


def designation_ref(designation: Designation) -> RefOut:
    return RefOut(public_id=designation.public_id, code=designation.code, name=designation.title)


def warnings_out(warnings: Sequence[OrgWarning]) -> list[WarningOut]:
    return [WarningOut(code=item.code, message=item.message) for item in warnings]


# ------------------------------------------------------------------------- unit types


def unit_types_out(db: Session, types: Sequence[OrgUnitType]) -> list[OrgUnitTypeOut]:
    rules: dict[int, list[OrgUnitTypeRule]] = defaultdict(list)
    for rule in all_rules(db):
        rules[rule.child_type_id].append(rule)
    by_id = {item.id: item for item in db.scalars(select(OrgUnitType))}
    result = []
    for unit_type in types:
        own = rules.get(unit_type.id, [])
        parents = sorted(
            (by_id[rule.parent_type_id] for rule in own if rule.parent_type_id is not None),
            key=lambda item: (item.sort_order, item.code),
        )
        result.append(
            OrgUnitTypeOut(
                public_id=unit_type.public_id,
                code=unit_type.code,
                name=unit_type.name,
                description=unit_type.description,
                sort_order=unit_type.sort_order,
                allows_employee_assignment=unit_type.allows_employee_assignment,
                is_active=unit_type.is_active,
                parent_rule_mode=unit_type.parent_rule_mode,  # type: ignore[arg-type]
                allow_root=any(rule.parent_type_id is None for rule in own),
                allowed_parent_types=[ref(parent) for parent in parents],
                translations=translations_of(unit_type.translations),
                version=unit_type.version,
                created_at=unit_type.created_at,
                updated_at=unit_type.updated_at,
            )
        )
    return result


def unit_type_out(db: Session, unit_type: OrgUnitType) -> OrgUnitTypeOut:
    return unit_types_out(db, [unit_type])[0]


# ------------------------------------------------------------------------------ units


def unit_status(unit: OrgUnit, as_of: date) -> UnitStatus:
    if unit.effective_from is not None and unit.effective_from > as_of:
        return "not_started"
    if unit.effective_to is not None and unit.effective_to <= as_of:
        return "closed"
    return "active"


class UnitPresenter:
    """Presents units for one ``as_of`` date (parents and paths resolved once)."""

    def __init__(self, db: Session, as_of: date) -> None:
        self.db = db
        self.as_of = as_of
        self.parent_of = parents_on(db, as_of)
        self._units: dict[int, OrgUnit] = {}

    def _load(self, ids: set[int]) -> None:
        missing = ids - self._units.keys()
        if missing:
            for unit in self.db.scalars(select(OrgUnit).where(OrgUnit.id.in_(missing))).unique():
                self._units[unit.id] = unit

    def many(self, units: Sequence[OrgUnit]) -> list[OrgUnitOut]:
        for unit in units:
            self._units[unit.id] = unit
        paths = {unit.id: ancestor_path(unit.id, self.parent_of) for unit in units}
        self._load({node for path in paths.values() for node in path})
        result = []
        for unit in units:
            path = [ref(self._units[node]) for node in paths[unit.id]]
            result.append(
                OrgUnitOut(
                    public_id=unit.public_id,
                    code=unit.code,
                    name=unit.name,
                    short_name=unit.short_name,
                    unit_type=ref(unit.unit_type),
                    location=ref(unit.location) if unit.location else None,
                    as_of=self.as_of,
                    parent=path[-1] if path else None,
                    path=path,
                    status=unit_status(unit, self.as_of),
                    effective_from=unit.effective_from,
                    effective_to=unit.effective_to,
                    external_ref=unit.external_ref,
                    translations=translations_of(unit.translations),
                    version=unit.version,
                    created_at=unit.created_at,
                    updated_at=unit.updated_at,
                )
            )
        return result

    def one(self, unit: OrgUnit) -> OrgUnitOut:
        return self.many([unit])[0]


def unit_write_out(
    db: Session, unit: OrgUnit, as_of: date, warnings: Sequence[OrgWarning] = ()
) -> OrgUnitWriteOut:
    return OrgUnitWriteOut(unit=UnitPresenter(db, as_of).one(unit), warnings=warnings_out(warnings))


def tree_out(units: Sequence[OrgUnit], parent_of: dict[int, int], as_of: date) -> OrgTreeOut:
    by_id = {unit.id: unit for unit in units}
    nodes = []
    for unit in units:
        parent = by_id.get(parent_of[unit.id]) if unit.id in parent_of else None
        nodes.append(
            OrgTreeNode(
                public_id=unit.public_id,
                code=unit.code,
                name=unit.name,
                short_name=unit.short_name,
                unit_type=ref(unit.unit_type),
                location=ref(unit.location) if unit.location else None,
                parent_id=parent.public_id if parent else None,
                status=unit_status(unit, as_of),
                translations=translations_of(unit.translations),
            )
        )
    return OrgTreeOut(as_of=as_of, nodes=nodes)


def history_out(unit: OrgUnit, links: Sequence[OrgUnitHierarchy]) -> UnitHistoryOut:
    return UnitHistoryOut(
        unit=ref(unit),
        effective_from=unit.effective_from,
        effective_to=unit.effective_to,
        placements=[
            HierarchyLinkOut(
                parent=ref(link.parent),
                effective_from=link.effective_from,
                effective_to=link.effective_to,
                recorded_at=link.created_at,
                ended_at=link.ended_at,
            )
            for link in links
        ],
    )


# -------------------------------------------------------------------------- locations


def location_out(location: Location) -> LocationOut:
    return LocationOut(
        public_id=location.public_id,
        code=location.code,
        name=location.name,
        address_line1=location.address_line1,
        address_line2=location.address_line2,
        city=location.city,
        state=location.state,
        postal_code=location.postal_code,
        country_code=location.country_code,
        time_zone=location.time_zone,
        is_active=location.is_active,
        version=location.version,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


# ------------------------------------------------------------------------- reference


def job_families_out(db: Session, families: Sequence[JobFamily]) -> list[JobFamilyOut]:
    parent_ids = {f.parent_job_family_id for f in families if f.parent_job_family_id}
    parents = (
        {p.id: p for p in db.scalars(select(JobFamily).where(JobFamily.id.in_(parent_ids)))}
        if parent_ids
        else {}
    )
    return [
        JobFamilyOut(
            public_id=family.public_id,
            code=family.code,
            name=family.name,
            description=family.description,
            parent=(
                ref(parents[family.parent_job_family_id])
                if family.parent_job_family_id in parents
                else None
            ),
            is_active=family.is_active,
            version=family.version,
            created_at=family.created_at,
            updated_at=family.updated_at,
        )
        for family in families
    ]


def ranked_out(item: Grade | JobLevel) -> RankedOut:
    return RankedOut(
        public_id=item.public_id,
        code=item.code,
        name=item.name,
        rank=item.rank,
        is_active=item.is_active,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def designation_out(designation: Designation) -> DesignationOut:
    return DesignationOut(
        public_id=designation.public_id,
        code=designation.code,
        title=designation.title,
        job_family=ref(designation.job_family) if designation.job_family else None,
        is_active=designation.is_active,
        translations=translations_of(designation.translations),
        version=designation.version,
        created_at=designation.created_at,
        updated_at=designation.updated_at,
    )


def functional_role_out(role: FunctionalRole) -> FunctionalRoleOut:
    return FunctionalRoleOut(
        public_id=role.public_id,
        code=role.code,
        name=role.name,
        description=role.description,
        job_family=ref(role.job_family) if role.job_family else None,
        owner_unit=ref(role.owner_org_unit) if role.owner_org_unit else None,
        is_active=role.is_active,
        translations=translations_of(role.translations),
        version=role.version,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def mapping_out(mapping: DesignationFunctionalRole) -> DesignationRoleMappingOut:
    return DesignationRoleMappingOut(
        public_id=mapping.public_id,
        designation=designation_ref(mapping.designation),
        functional_role=ref(mapping.functional_role),
        scope_unit=ref(mapping.scope_org_unit) if mapping.scope_org_unit else None,
        include_descendants=mapping.scope_include_descendants,
        effective_from=mapping.effective_from,
        effective_to=mapping.effective_to,
        created_at=mapping.created_at,
        ended_at=mapping.ended_at,
    )


def responsibility_out(item: Responsibility) -> ResponsibilityOut:
    return ResponsibilityOut(
        public_id=item.public_id,
        code=item.code,
        name=item.name,
        description=item.description,
        category=item.category,
        is_active=item.is_active,
        translations=translations_of(item.translations),
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
