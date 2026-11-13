"""Stage B: append-only protection for audit_event (database layer).

Adds BEFORE UPDATE and BEFORE DELETE triggers that reject any UPDATE or DELETE
statement on audit_event, for every account (including the runtime account).

Prerequisite on servers with binary logging enabled: the creating account needs
SUPER/SET_USER_ID, or ``log_bin_trust_function_creators = 1``. The local
development server uses the latter (approved for local development only).

LIMITATIONS — these triggers do NOT make the audit trail tamper-proof:
* ``TRUNCATE TABLE`` and ``DROP TABLE`` do not fire row triggers. Any account with
  DROP privilege on the schema (the migration account, DBAs) can still remove
  audit data. The runtime account has no DROP/ALTER/TRIGGER privileges.
* An account with TRIGGER privilege (the migration account) can drop these
  triggers. Production protection needs a separate DBA decision (see ADR).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12 11:58:17.831932+00:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NO_UPDATE = "trg_audit_event_no_update"
NO_DELETE = "trg_audit_event_no_delete"


def upgrade() -> None:
    """Create the two append-only triggers."""
    op.execute(
        f"CREATE TRIGGER {NO_UPDATE} BEFORE UPDATE ON audit_event FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' "
        "SET MESSAGE_TEXT = 'audit_event is append-only; updates are not permitted'"
    )
    op.execute(
        f"CREATE TRIGGER {NO_DELETE} BEFORE DELETE ON audit_event FOR EACH ROW "
        "SIGNAL SQLSTATE '45000' "
        "SET MESSAGE_TEXT = 'audit_event is append-only; deletes are not permitted'"
    )


def downgrade() -> None:
    """Drop the triggers (audit rows themselves are untouched)."""
    op.execute(f"DROP TRIGGER IF EXISTS {NO_DELETE}")
    op.execute(f"DROP TRIGGER IF EXISTS {NO_UPDATE}")
