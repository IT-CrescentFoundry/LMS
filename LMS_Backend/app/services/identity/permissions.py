"""Permission and role codes referenced by application code.

The authoritative definitions (descriptions, role mappings) are seeded by the
Alembic revision ``seed_access_roles_permissions``; an integration test verifies
that every code below exists in the database after migration.

Business logic checks **permissions**, never role names. The only role code used
in code is ``SUPER_ADMIN_ROLE``, by the controlled CLI bootstrap commands.
"""

from enum import StrEnum


class Permission(StrEnum):
    # Implemented in Stage B
    USER_ACCOUNTS_VIEW = "user_accounts.view"
    USER_ACCOUNTS_MANAGE = "user_accounts.manage"
    USER_SESSIONS_REVOKE = "user_sessions.revoke"
    USER_ROLES_ASSIGN = "user_roles.assign"
    USER_ROLES_ASSIGN_ADMIN = "user_roles.assign_admin"
    ACCESS_ROLES_VIEW = "access_roles.view"
    ACCESS_ROLES_MANAGE = "access_roles.manage"
    AUDIT_VIEW = "audit.view"
    # Stage C1 — organisation structure and reference data (revision 0007)
    ORGANISATION_VIEW = "organisation.view"
    ORGANISATION_MANAGE = "organisation.manage"
    DESIGNATIONS_MANAGE = "designations.manage"
    FUNCTIONAL_ROLES_MANAGE = "functional_roles.manage"
    RESPONSIBILITIES_MANAGE = "responsibilities.manage"
    # Stage C3 - employee master (revision 0009; interim global-only matrix, Q-51)
    EMPLOYEES_VIEW = "employees.view"
    EMPLOYEES_HISTORY_VIEW = "employees.history.view"
    EMPLOYEES_MANAGE = "employees.manage"
    REPORTING_LINES_MANAGE = "reporting_lines.manage"
    # Stage D: imports (migration 0010)
    IMPORTS_VIEW = "imports.view"
    IMPORTS_EMPLOYEES_RUN = "imports.employees.run"
    IMPORTS_EMPLOYEES_COMMIT = "imports.employees.commit"
    IMPORTS_MAPPINGS_MANAGE = "imports.mappings.manage"
    # First release: training register, skill matrix (migration 0011)
    TRAINING_RECORDS_VIEW = "training.records.view"
    COMPETENCY_VIEW = "competency.view"
    COMPETENCY_MANAGE = "competency.manage"
    COMPETENCY_ASSESS = "competency.assess"
    IMPORTS_ORGANISATION_RUN = "imports.organisation.run"
    IMPORTS_ORGANISATION_COMMIT = "imports.organisation.commit"
    # Seeded in Stage B; first used by the training register (0011):
    # learning.own.view (own schedule/history/skills), team.learning.view (team),
    # training_events.manage (programmes, events, sessions, participation).
    # Capabilities for later stages (no endpoints yet)
    LEARNING_OWN_VIEW = "learning.own.view"
    CERTIFICATES_OWN_VIEW = "certificates.own.view"
    TRAINING_REQUESTS_SUBMIT = "training_requests.submit"
    TEAM_LEARNING_VIEW = "team.learning.view"
    LEARNING_CONTENT_MANAGE = "learning_content.manage"
    LEARNING_CONTENT_REVIEW = "learning_content.review"
    LEARNING_CONTENT_PUBLISH = "learning_content.publish"
    TRAINING_EVENTS_MANAGE = "training_events.manage"
    SETTINGS_MANAGE = "settings.manage"


SUPER_ADMIN_ROLE = "super_admin"
DEFAULT_ROLE = "employee"
