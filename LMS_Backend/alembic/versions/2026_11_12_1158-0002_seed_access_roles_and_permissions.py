"""Stage B: seed access permissions, access roles and their mappings (data only).

Initial access roles (system access roles, NOT functional job roles):
employee, supervisor, hod, sme, hr_admin, super_admin.

Assignment rules encoded here (enforced by the application):
* employee / supervisor / hod / sme are granted with ``user_roles.assign`` (HR Admin);
* hr_admin is granted with ``user_roles.assign_admin`` (privileged: Super Admin only);
* super_admin is not API-assignable at all (CLI bootstrap/grant commands only).

Privileged permissions are held only by super_admin. Several permissions describe
capabilities of later stages; they grant nothing until those endpoints exist.

No user accounts are created. This file deliberately does not import application
code: the seed is a frozen snapshot, and later changes are made by new revisions.
Timestamps use the server's UTC_TIMESTAMP(6).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12 11:58:15.127141+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

permission = sa.table(
    "access_permission",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("description", sa.String),
    sa.column("is_privileged", sa.Boolean),
    sa.column("created_at", sa.DateTime),
)
role = sa.table(
    "access_role",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("is_system", sa.Boolean),
    sa.column("is_api_assignable", sa.Boolean),
    sa.column("assign_permission_id", sa.BigInteger),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
    sa.column("version", sa.Integer),
)
role_permission = sa.table(
    "access_role_permission",
    sa.column("access_role_id", sa.BigInteger),
    sa.column("access_permission_id", sa.BigInteger),
    sa.column("granted_at", sa.DateTime),
)

# (code, is_privileged, description)
PERMISSIONS: list[tuple[str, bool, str]] = [
    ("user_accounts.view", False, "View user accounts"),
    (
        "user_accounts.manage",
        False,
        "Create, update, activate, suspend and disable user accounts; reset passwords",
    ),
    ("user_sessions.revoke", False, "Revoke users' login sessions"),
    (
        "user_roles.assign",
        False,
        "Grant and revoke standard access roles (Employee, SME, Supervisor, HOD)",
    ),
    ("user_roles.assign_admin", True, "Grant and revoke the HR Admin access role"),
    ("access_roles.view", False, "View access roles and permissions"),
    ("access_roles.manage", True, "Change the permissions of access roles"),
    ("audit.view", False, "View audit records"),
    ("learning.own.view", False, "View own learning"),
    ("certificates.own.view", False, "View own certificates"),
    ("training_requests.submit", False, "Submit training requests"),
    ("team.learning.view", False, "View team learning progress"),
    ("learning_content.manage", False, "Create and maintain learning content"),
    ("learning_content.review", False, "Review and validate learning content (SME)"),
    ("learning_content.publish", False, "Approve and publish learning content (HR)"),
    ("training_events.manage", False, "Manage training events"),
    ("settings.manage", True, "Configure LMS settings"),
]

_EMPLOYEE = ["learning.own.view", "certificates.own.view", "training_requests.submit"]
_HR_ADMIN = [
    *_EMPLOYEE,
    "team.learning.view",
    "learning_content.manage",
    "learning_content.review",
    "learning_content.publish",
    "training_events.manage",
    "user_accounts.view",
    "user_accounts.manage",
    "user_sessions.revoke",
    "user_roles.assign",
    "access_roles.view",
    "audit.view",
]

# (code, name, description, is_api_assignable, assign_permission_code, permission codes)
ROLES: list[tuple[str, str, str, bool, str | None, list[str]]] = [
    (
        "employee",
        "Employee",
        "Baseline access for every employee: own learning, certificates and requests.",
        True,
        "user_roles.assign",
        _EMPLOYEE,
    ),
    (
        "supervisor",
        "Supervisor",
        "Employee access plus visibility of team learning progress.",
        True,
        "user_roles.assign",
        [*_EMPLOYEE, "team.learning.view"],
    ),
    (
        "hod",
        "HOD",
        "Head of department: employee access plus team learning visibility.",
        True,
        "user_roles.assign",
        [*_EMPLOYEE, "team.learning.view"],
    ),
    (
        "sme",
        "SME",
        "Subject-matter expert: employee access plus technical content review.",
        True,
        "user_roles.assign",
        [*_EMPLOYEE, "learning_content.review"],
    ),
    (
        "hr_admin",
        "HR Admin",
        "HR administration: accounts, standard roles, content approval, training, audit.",
        True,
        "user_roles.assign_admin",
        _HR_ADMIN,
    ),
    (
        "super_admin",
        "Super Admin",
        "Full system administration. Granted only through the controlled CLI commands.",
        False,
        None,
        [code for code, _privileged, _description in PERMISSIONS],
    ),
]

NOW = sa.func.utc_timestamp(6)


def upgrade() -> None:
    """Insert the permissions, roles and role-permission mappings."""
    for code, privileged, description in PERMISSIONS:
        op.execute(
            permission.insert().values(
                code=code, description=description, is_privileged=privileged, created_at=NOW
            )
        )

    columns = [
        "code",
        "name",
        "description",
        "is_system",
        "is_api_assignable",
        "assign_permission_id",
        "created_at",
        "updated_at",
        "version",
    ]
    for code, name, description, api_assignable, assign_code, _codes in ROLES:
        if assign_code is None:
            op.execute(
                role.insert().values(
                    code=code,
                    name=name,
                    description=description,
                    is_system=True,
                    is_api_assignable=api_assignable,
                    assign_permission_id=None,
                    created_at=NOW,
                    updated_at=NOW,
                    version=1,
                )
            )
        else:
            op.execute(
                role.insert().from_select(
                    columns,
                    sa.select(
                        sa.literal(code),
                        sa.literal(name),
                        sa.literal(description),
                        sa.literal(True),
                        sa.literal(api_assignable),
                        permission.c.id,
                        NOW,
                        NOW,
                        sa.literal(1),
                    ).where(permission.c.code == assign_code),
                )
            )

    for code, _name, _description, _api, _assign, permission_codes in ROLES:
        # Explicit cross join (ON true), narrowed to one role and its permission codes.
        op.execute(
            role_permission.insert().from_select(
                ["access_role_id", "access_permission_id", "granted_at"],
                sa.select(role.c.id, permission.c.id, NOW)
                .select_from(role.join(permission, sa.true()))
                .where(role.c.code == code, permission.c.code.in_(permission_codes)),
            )
        )


def downgrade() -> None:
    """Remove exactly the seeded rows.

    Fails (by foreign key) if any account still holds a seeded role, so a downgrade
    can never silently strip access from existing users.
    """
    role_codes = [code for code, *_rest in ROLES]
    op.execute(
        role_permission.delete().where(
            role_permission.c.access_role_id.in_(
                sa.select(role.c.id).where(role.c.code.in_(role_codes))
            )
        )
    )
    op.execute(role.delete().where(role.c.code.in_(role_codes)))
    op.execute(
        permission.delete().where(permission.c.code.in_([code for code, *_rest in PERMISSIONS]))
    )
