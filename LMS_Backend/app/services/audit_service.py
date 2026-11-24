"""Central audit-event recording.

``record_audit_event`` adds the event to the caller's session, so it commits (or
rolls back) atomically with the change it describes. It never commits by itself.

Metadata must be small, structured and free of secrets: keys that suggest secrets
(password, token, secret, hash, csrf, cookie, credential) are rejected outright.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.models.audit import AuditEvent, AuditOutcome


class AuditEventType(StrEnum):
    LOGIN_SUCCEEDED = "auth.login.succeeded"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_THROTTLED = "auth.login.throttled"
    LOGIN_DENIED_INACTIVE = "auth.login.denied_inactive"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"  # noqa: S105 - audit event code, not a credential
    PASSWORD_CHANGE_FAILED = "auth.password.change_failed"  # noqa: S105 - audit event code, not a credential
    ACCOUNT_CREATED = "user_account.created"
    ACCOUNT_UPDATED = "user_account.updated"
    ACCOUNT_ACTIVATED = "user_account.activated"
    ACCOUNT_SUSPENDED = "user_account.suspended"
    ACCOUNT_DISABLED = "user_account.disabled"
    ACCOUNT_PASSWORD_RESET = "user_account.password_reset"  # noqa: S105 - audit event code, not a credential
    SESSION_REVOKED = "user_session.revoked"
    SESSIONS_REVOKED_ALL = "user_session.revoked_all"
    ROLE_GRANTED = "access_role.granted"
    ROLE_REVOKED = "access_role.revoked"
    ROLE_PERMISSION_GRANTED = "access_role.permission_granted"
    ROLE_PERMISSION_REVOKED = "access_role.permission_revoked"
    SUPER_ADMIN_BOOTSTRAPPED = "super_admin.bootstrapped"
    SUPER_ADMIN_GRANTED = "super_admin.granted"
    SUPER_ADMIN_REVOKED = "super_admin.revoked"
    AUTHORIZATION_DENIED = "authorization.denied"
    AUDIT_VIEWED = "audit.events.viewed"
    # Stage C1 — organisation structure and reference data
    ORG_UNIT_TYPE_CREATED = "org_unit_type.created"
    ORG_UNIT_TYPE_UPDATED = "org_unit_type.updated"
    ORG_UNIT_TYPE_RULES_CHANGED = "org_unit_type.parent_rules_changed"
    ORG_UNIT_CREATED = "org_unit.created"
    ORG_UNIT_CORRECTED = "org_unit.corrected"
    ORG_UNIT_MOVED = "org_unit.moved"
    ORG_UNIT_CLOSED = "org_unit.closed"
    ORG_UNIT_REOPENED = "org_unit.reopened"
    LOCATION_CREATED = "location.created"
    LOCATION_UPDATED = "location.updated"
    JOB_FAMILY_CREATED = "job_family.created"
    JOB_FAMILY_UPDATED = "job_family.updated"
    GRADE_CREATED = "grade.created"
    GRADE_UPDATED = "grade.updated"
    JOB_LEVEL_CREATED = "job_level.created"
    JOB_LEVEL_UPDATED = "job_level.updated"
    DESIGNATION_CREATED = "designation.created"
    DESIGNATION_UPDATED = "designation.updated"
    FUNCTIONAL_ROLE_CREATED = "functional_role.created"
    FUNCTIONAL_ROLE_UPDATED = "functional_role.updated"
    DESIGNATION_ROLE_MAPPED = "designation_role_mapping.created"
    DESIGNATION_ROLE_MAPPING_ENDED = "designation_role_mapping.ended"
    RESPONSIBILITY_CREATED = "responsibility.created"
    RESPONSIBILITY_UPDATED = "responsibility.updated"
    # Stage C3 - employees (target: the employee; metadata names the sub-record)
    EMPLOYEE_CREATED = "employee.created"
    EMPLOYEE_CORRECTED = "employee.corrected"
    EMPLOYEE_STATUS_CHANGED = "employee.status_changed"
    ASSIGNMENT_CREATED = "employee_assignment.created"
    ASSIGNMENT_CHANGED = "employee_assignment.changed"
    ASSIGNMENT_ENDED = "employee_assignment.ended"
    ASSIGNMENT_CORRECTED = "employee_assignment.corrected"
    EMPLOYEE_ROLE_ASSIGNED = "employee_functional_role.assigned"
    EMPLOYEE_ROLE_EXCLUDED = "employee_functional_role.excluded"
    EMPLOYEE_ROLE_ENDED = "employee_functional_role.ended"
    EMPLOYEE_RESPONSIBILITY_ASSIGNED = "employee_responsibility.assigned"
    EMPLOYEE_RESPONSIBILITY_ENDED = "employee_responsibility.ended"
    REPORTING_CREATED = "reporting_relationship.created"
    REPORTING_ENDED = "reporting_relationship.ended"
    EMPLOYEE_ACCOUNT_LINKED = "employee_account.linked"
    EMPLOYEE_ACCOUNT_UNLINKED = "employee_account.unlinked"
    # Stage D imports (metadata never contains workbook cell values)
    IMPORT_UPLOADED = "import.job.uploaded"
    IMPORT_UPLOAD_REJECTED = "import.upload.rejected"
    IMPORT_MAPPING_SET = "import.job.mapping_set"
    IMPORT_VALIDATED = "import.job.validated"
    IMPORT_ROW_DECIDED = "import.row.decided"
    IMPORT_COMMITTED = "import.job.committed"
    IMPORT_COMMIT_FAILED = "import.job.commit_failed"
    IMPORT_CANCELLED = "import.job.cancelled"
    IMPORT_EXPIRED = "import.job.expired"
    IMPORT_VALIDATION_ABANDONED = "import.job.validation_abandoned"
    IMPORT_VALUE_MAPPING_APPROVED = "import.mapping.approved"
    IMPORT_VALUE_MAPPING_REJECTED = "import.mapping.rejected"
    IMPORT_VALUE_MAPPING_SUPERSEDED = "import.mapping.superseded"
    # First release (0011): training register, competency, skill matrix
    TRAINING_PROGRAMME_CREATED = "training_programme.created"
    TRAINING_PROGRAMME_UPDATED = "training_programme.updated"
    TRAINING_EVENT_CREATED = "training_event.created"
    TRAINING_EVENT_UPDATED = "training_event.updated"
    TRAINING_EVENT_STATUS_CHANGED = "training_event.status_changed"
    TRAINING_SESSION_CREATED = "training_session.created"
    TRAINING_SESSION_UPDATED = "training_session.updated"
    TRAINING_PARTICIPANT_ADDED = "training_participation.added"
    TRAINING_PARTICIPATION_UPDATED = "training_participation.updated"
    PROFICIENCY_SCALE_CREATED = "proficiency_scale.created"
    PROFICIENCY_SCALE_UPDATED = "proficiency_scale.updated"
    COMPETENCY_CREATED = "competency.created"
    COMPETENCY_UPDATED = "competency.updated"
    COMPETENCY_STATUS_CHANGED = "competency.status_changed"
    COMPETENCY_BAND_REQUIREMENTS_CHANGED = "competency.band_requirements_changed"
    SKILL_MATRIX_CREATED = "skill_matrix.created"
    SKILL_MATRIX_UPDATED = "skill_matrix.updated"
    SKILL_MATRIX_ITEMS_CHANGED = "skill_matrix.items_changed"
    SKILL_MATRIX_MEMBERS_CHANGED = "skill_matrix.members_changed"
    COMPETENCY_ASSESSMENT_RECORDED = "competency_assessment.recorded"


class TargetType(StrEnum):
    USER_ACCOUNT = "user_account"
    USER_SESSION = "user_session"
    ACCESS_ROLE = "access_role"
    ORG_UNIT_TYPE = "org_unit_type"
    ORG_UNIT = "org_unit"
    LOCATION = "location"
    JOB_FAMILY = "job_family"
    GRADE = "grade"
    JOB_LEVEL = "job_level"
    DESIGNATION = "designation"
    FUNCTIONAL_ROLE = "functional_role"
    DESIGNATION_ROLE_MAPPING = "designation_role_mapping"
    RESPONSIBILITY = "responsibility"
    EMPLOYEE = "employee"
    IMPORT_JOB = "import_job"
    IMPORT_VALUE_MAPPING = "import_value_mapping"
    TRAINING_PROGRAMME = "training_programme"
    TRAINING_EVENT = "training_event"
    PROFICIENCY_SCALE = "proficiency_scale"
    COMPETENCY = "competency"
    SKILL_MATRIX = "skill_matrix"


_FORBIDDEN_KEY_FRAGMENTS = ("password", "token", "secret", "hash", "csrf", "cookie", "credential")


class UnsafeAuditMetadataError(ValueError):
    """Raised when audit metadata contains a key that could hold a secret."""


def _check_metadata(value: Any, path: str = "metadata") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise UnsafeAuditMetadataError(f"Audit {path} may not contain key {key!r}.")
            _check_metadata(child, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for item in value:
            _check_metadata(item, path)


def record_audit_event(
    db: Session,
    *,
    event_type: AuditEventType,
    outcome: AuditOutcome,
    meta: RequestMeta,
    actor_user_id: int | None = None,
    target_type: TargetType | None = None,
    target_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AuditEvent:
    if metadata is not None:
        _check_metadata(metadata)
    event = AuditEvent(
        event_type=event_type.value,
        outcome=outcome.value,
        actor_user_id=actor_user_id,
        target_type=target_type.value if target_type else None,
        target_id=target_id,
        request_id=meta.request_id,
        source_ip=meta.ip_address,
        user_agent=meta.user_agent,
        event_metadata=dict(metadata) if metadata is not None else None,
    )
    db.add(event)
    return event
