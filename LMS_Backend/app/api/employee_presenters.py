"""Convert employee ORM objects into response schemas (Stage C3)."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from app.api.org_presenters import designation_ref, ref
from app.api.presenters import audit_events_out
from app.models.audit import AuditEvent
from app.models.employees import (
    Employee,
    EmployeeAssignment,
    EmployeeFunctionalRole,
    EmployeeResponsibility,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.models.identity import AccountStatus, UserAccount
from app.models.occupation import Grade, JobLevel, Responsibility
from app.schemas.audit import AuditEventOut
from app.schemas.employees import (
    AccountRef,
    AssignmentOut,
    DerivedFromOut,
    DirectReportOut,
    EffectiveRoleOut,
    EmployeeAccountOut,
    EmployeeOut,
    EmployeeRef,
    EmployeeSummary,
    ReportingRecordOut,
    ReportingTypeOut,
    ResponsibilityRecordOut,
    RoleRecordOut,
    SeparationPreviewOut,
    SeparationRecordOut,
)
from app.schemas.organisation import RefOut
from app.services.employees.accounts import AccountSummary
from app.services.employees.employees import (
    EmployeeContext,
    SeparationImpact,
    load_context,
)
from app.services.employees.roles import EffectiveRole
from app.services.organisation.support import translations_of


def _named(item: Grade | JobLevel | Responsibility) -> RefOut:
    return RefOut(public_id=item.public_id, code=item.code, name=item.name)


def employee_ref(employee: Employee) -> EmployeeRef:
    return EmployeeRef(
        public_id=employee.public_id,
        employee_code=employee.employee_code,
        full_name=employee.full_name,
        employment_status=employee.employment_status,  # type: ignore[arg-type]
    )


def account_ref(account: UserAccount) -> AccountRef:
    return AccountRef(
        public_id=account.public_id,
        login_id=account.login_id,
        display_name=account.display_name,
        status=account.status,
    )


def _summary_fields(employee: Employee, context: EmployeeContext, as_of: date) -> dict[str, object]:
    primary = context.primary
    location = None
    if primary is not None:
        location = primary.location or primary.org_unit.location
    return {
        "public_id": employee.public_id,
        "employee_code": employee.employee_code,
        "full_name": employee.full_name,
        "display_name": employee.display_name,
        "employment_status": employee.employment_status,
        "as_of": as_of,
        "primary_unit": ref(primary.org_unit) if primary else None,
        "path": [ref(unit) for unit in context.path],
        "designation": designation_ref(primary.designation)
        if primary and primary.designation
        else None,
        "location": ref(location) if location else None,
        "line_manager": employee_ref(context.line_manager) if context.line_manager else None,
        "has_active_account": any(
            account.status != AccountStatus.DISABLED.value for account in context.accounts
        ),
    }


def employee_summaries(
    db: Session, employees: Sequence[Employee], as_of: date
) -> list[EmployeeSummary]:
    contexts = load_context(db, list(employees), as_of)
    return [
        EmployeeSummary.model_validate(_summary_fields(item, contexts[item.id], as_of))
        for item in employees
    ]


def employee_out(db: Session, employee: Employee, as_of: date) -> EmployeeOut:
    context = load_context(db, [employee], as_of)[employee.id]
    return EmployeeOut.model_validate(
        {
            **_summary_fields(employee, context, as_of),
            "preferred_language": employee.preferred_language,
            "work_email": employee.work_email,
            "date_of_joining": employee.date_of_joining,
            "date_of_separation": employee.date_of_separation,
            "external_ref": employee.external_ref,
            "accounts": [account_ref(account) for account in context.accounts],
            "version": employee.version,
            "created_at": employee.created_at,
            "updated_at": employee.updated_at,
        }
    )


def assignment_out(row: EmployeeAssignment) -> AssignmentOut:
    return AssignmentOut.model_validate(
        {
            "public_id": row.public_id,
            "assignment_type": row.assignment_type,
            "org_unit": ref(row.org_unit),
            "designation": designation_ref(row.designation) if row.designation else None,
            "grade": _named(row.grade) if row.grade else None,
            "job_level": _named(row.job_level) if row.job_level else None,
            "location": ref(row.location) if row.location else None,
            "effective_from": row.effective_from,
            "effective_to": row.effective_to,
            "source": row.source,
            "reason": row.reason,
            "version": row.version,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


def role_record_out(record: EmployeeFunctionalRole) -> RoleRecordOut:
    return RoleRecordOut.model_validate(
        {
            "public_id": record.public_id,
            "functional_role": ref(record.functional_role),
            "kind": record.kind,
            "effective_from": record.effective_from,
            "effective_to": record.effective_to,
            "reason": record.reason,
            "created_at": record.created_at,
        }
    )


def effective_role_out(item: EffectiveRole) -> EffectiveRoleOut:
    return EffectiveRoleOut(
        functional_role=ref(item.role),
        effective=item.effective,
        derived_from=[
            DerivedFromOut.model_validate(
                {
                    "assignment": assignment.public_id,
                    "assignment_type": assignment.assignment_type,
                    "org_unit": ref(assignment.org_unit),
                    "designation": designation_ref(mapping.designation),
                    "mapping": mapping.public_id,
                }
            )
            for assignment, mapping in item.derived_from
        ],
        manual=role_record_out(item.manual) if item.manual else None,
        exclusion=role_record_out(item.exclusion) if item.exclusion else None,
    )


def responsibility_out(record: EmployeeResponsibility) -> ResponsibilityRecordOut:
    return ResponsibilityRecordOut(
        public_id=record.public_id,
        responsibility=_named(record.responsibility),
        context_unit=ref(record.context_org_unit) if record.context_org_unit else None,
        context_location=ref(record.context_location) if record.context_location else None,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        reason=record.reason,
        created_at=record.created_at,
    )


def reporting_type_out(item: ReportingRelationshipType) -> ReportingTypeOut:
    return ReportingTypeOut(
        public_id=item.public_id,
        code=item.code,
        name=item.name,
        allows_multiple=item.allows_multiple,
        is_hierarchical=item.is_hierarchical,
        is_active=item.is_active,
        translations=translations_of(item.translations),
    )


def reporting_record_out(record: ReportingRelationship) -> ReportingRecordOut:
    relationship_type = record.relationship_type
    return ReportingRecordOut(
        public_id=record.public_id,
        relationship_type=RefOut(
            public_id=relationship_type.public_id,
            code=relationship_type.code,
            name=relationship_type.name,
        ),
        employee=employee_ref(record.employee),
        manager=employee_ref(record.manager),
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        reason=record.reason,
        created_at=record.created_at,
    )


def employee_events_out(db: Session, events: Sequence[AuditEvent]) -> list[AuditEventOut]:
    """Audit events for employee views, without network details.

    The actor's source IP and user agent stay in the audit log (``audit.view``, where
    every read is itself audited); HR views of an employee's history do not need them.
    """
    return [
        event.model_copy(update={"source_ip": None, "user_agent": None})
        for event in audit_events_out(db, events)
    ]


def separation_preview_out(impact: SeparationImpact) -> SeparationPreviewOut:
    own = [
        SeparationRecordOut.model_validate(
            {
                "record_id": record.public_id,
                "kind": record.kind,
                "code": record.label,
                "name": record.name,
                "effective_from": record.row.effective_from,
                "effective_to": record.row.effective_to,
                "starts_after_separation": record.starts_after,
            }
        )
        for record in impact.own_records
    ]
    reports = [
        DirectReportOut(
            record_id=record.public_id,
            employee=employee_ref(record.row.employee),
            relationship_type=RefOut(
                public_id=record.row.relationship_type.public_id,
                code=record.row.relationship_type.code,
                name=record.row.relationship_type.name,
            ),
            effective_from=record.row.effective_from,
            effective_to=record.row.effective_to,
            starts_after_separation=record.starts_after,
        )
        for record in impact.direct_reports
    ]
    return SeparationPreviewOut(
        employee=employee_ref(impact.employee),
        version=impact.employee.version,
        separation_date=impact.separation_date,
        records_end_on=impact.records_end_on,
        own_records=own,
        direct_reports=reports,
        requires_end_open_records=any(not r.starts_after for r in impact.own_records),
        requires_end_direct_reports=any(not r.starts_after for r in impact.direct_reports),
        blocked=impact.blocked,
    )


def employee_account_out(db: Session, summary: AccountSummary) -> EmployeeAccountOut:
    return EmployeeAccountOut(
        accounts=[account_ref(account) for account in summary.accounts],
        flags=summary.flags,
        history=employee_events_out(db, summary.history),
    )
