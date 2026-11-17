"""Generated-column verification against MySQL's information_schema.

Alembic autogenerate cannot compare these expressions: MySQL stores string literals
with charset introducers (``_utf8mb4'primary'``), so the drift test only warns (the
warnings are deliberately left visible). This test checks the substance instead.

Only engine-specific formatting is normalised - charset introducers, escaped quotes,
backticks, letter case and whitespace. Parentheses, operators, operands, literals and
their order are compared exactly against the pinned MySQL form, and the pinned form
is tied to the model's own expression token by token.
"""

import re

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers every table)
from app.db.base import Base
from tests.support.database import assert_connected_to

pytestmark = pytest.mark.db

# Expected MySQL form (MySQL adds the grouping parentheses itself).
EXPECTED = {
    ("employee_assignment", "is_primary"): "(assignment_type = 'primary')",
    ("employee_assignment", "primary_open"): (
        "if(((assignment_type = 'primary') and (effective_to is null)),1,null)"
    ),
    ("user_account", "linked_employee_active"): (
        "if(((employee_id is not null) and (status <> 'disabled')),employee_id,null)"
    ),
    # Stage D (0010): one current (non-superseded) mapping decision per kind and label.
    ("import_value_mapping", "current_flag"): "if((status <> 'superseded'),1,null)",
}
_INTRODUCER = re.compile(r"_[a-z0-9]+(?=')", re.IGNORECASE)
_TOKEN = re.compile(r"'[^']*'|<>|!=|<=|>=|=|<|>|,|[a-z_][a-z0-9_]*|\d+", re.IGNORECASE)
_STORED_LINKED = (
    "if(((`employee_id` is not null) and (`status` <> _utf8mb4\\'disabled\\')),`employee_id`,NULL)"
)


def normalise(expression: str) -> str:
    """Remove engine formatting only; keep every operand, operator and parenthesis."""
    value = expression.replace("\\'", "'").replace("`", "")
    value = _INTRODUCER.sub("", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\s*([(),])\s*", r"\1", value)


def tokens(expression: str) -> list[str]:
    """Operands, operators and literals in order (grouping parentheses ignored)."""
    return [token.lower() for token in _TOKEN.findall(normalise(expression))]


def test_normalisation_removes_only_formatting() -> None:
    expected = normalise(EXPECTED[("user_account", "linked_employee_active")])
    assert normalise(_STORED_LINKED) == expected
    # A substantive difference is never normalised away.
    for original, changed in (("<>", "="), ("disabled", "suspended"), (" and ", " or ")):
        assert normalise(_STORED_LINKED.replace(original, changed)) != expected, changed
    assert normalise("(a or b) and c") != normalise("a or (b and c)")


@pytest.mark.parametrize(("table", "column"), list(EXPECTED))
def test_generated_column_matches_the_expected_expression(
    db: Session, test_database_name: str, table: str, column: str
) -> None:
    connection = db.connection()
    assert_connected_to(connection, test_database_name)  # SELECT DATABASE(), CURRENT_USER()
    actual, extra = connection.execute(
        text(
            "SELECT GENERATION_EXPRESSION, EXTRA FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
        ),
        {"t": table, "c": column},
    ).one()
    assert "STORED GENERATED" in extra.upper(), extra
    assert normalise(actual) == normalise(EXPECTED[(table, column)]), actual

    # The pinned form is the model's expression: same operands, operators and order.
    computed = Base.metadata.tables[table].c[column].computed
    assert computed is not None and computed.persisted is True
    assert tokens(str(computed.sqltext)) == tokens(EXPECTED[(table, column)])
