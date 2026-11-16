"""SQLAlchemy ORM models.

Every model module must be imported here so that ``Base.metadata`` is complete
when Alembic compares it with the database (autogenerate).

The proposed schema for later stages is documented in
``docs/database/LMS_DATABASE_DESIGN.md``.
"""

from app.db.base import Base
from app.models.audit import AuditEvent, AuditOutcome
from app.models.employees import (
    AssignmentSource,
    AssignmentType,
    Employee,
    EmployeeAssignment,
    EmployeeFunctionalRole,
    EmployeeResponsibility,
    EmploymentStatus,
    FunctionalRoleKind,
    ReportingRelationship,
    ReportingRelationshipType,
    ReportingRelationshipTypeTranslation,
)
from app.models.identity import (
    AccessPermission,
    AccessRole,
    AccessRolePermission,
    AccountStatus,
    LoginThrottle,
    ThrottleScope,
    UserAccessRole,
    UserAccount,
    UserSession,
)
from app.models.occupation import (
    Designation,
    DesignationFunctionalRole,
    DesignationTranslation,
    FunctionalRole,
    FunctionalRoleTranslation,
    Grade,
    JobFamily,
    JobLevel,
    Responsibility,
    ResponsibilityTranslation,
)
from app.models.organisation import (
    GraphLock,
    Location,
    OrgUnit,
    OrgUnitHierarchy,
    OrgUnitTranslation,
    OrgUnitType,
    OrgUnitTypeRule,
    OrgUnitTypeTranslation,
    ParentRuleMode,
)

__all__ = [
    "AccessPermission",
    "AccessRole",
    "AccessRolePermission",
    "AccountStatus",
    "AssignmentSource",
    "AssignmentType",
    "AuditEvent",
    "AuditOutcome",
    "Base",
    "Designation",
    "DesignationFunctionalRole",
    "DesignationTranslation",
    "Employee",
    "EmployeeAssignment",
    "EmployeeFunctionalRole",
    "EmployeeResponsibility",
    "EmploymentStatus",
    "FunctionalRole",
    "FunctionalRoleKind",
    "FunctionalRoleTranslation",
    "Grade",
    "GraphLock",
    "JobFamily",
    "JobLevel",
    "Location",
    "LoginThrottle",
    "OrgUnit",
    "OrgUnitHierarchy",
    "OrgUnitTranslation",
    "OrgUnitType",
    "OrgUnitTypeRule",
    "OrgUnitTypeTranslation",
    "ParentRuleMode",
    "ReportingRelationship",
    "ReportingRelationshipType",
    "ReportingRelationshipTypeTranslation",
    "Responsibility",
    "ResponsibilityTranslation",
    "ThrottleScope",
    "UserAccessRole",
    "UserAccount",
    "UserSession",
]
