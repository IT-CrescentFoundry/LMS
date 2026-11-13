"""Unit tests for passwords, tokens, identifiers, throttling maths and column types."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr

from app.core.ids import uuid7
from app.core.security.passwords import (
    PasswordIssue,
    hash_password,
    needs_rehash,
    password_policy_issues,
    verify_against_dummy,
    verify_password,
)
from app.core.security.tokens import (
    csrf_token_for,
    csrf_token_matches,
    generate_session_token,
    hash_session_token,
    keyed_digest,
)
from app.db.types import UTCDateTime, UUIDBinary
from app.services.identity.throttling import next_failure_state

SECRET = SecretStr("unit-test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz")


# --- Passwords ------------------------------------------------------------------


def test_password_hash_is_argon2id_and_verifies() -> None:
    hashed = hash_password("Correct horse battery staple")

    assert hashed.startswith("$argon2id$")
    assert "Correct horse" not in hashed
    assert verify_password(hashed, "Correct horse battery staple") is True
    assert verify_password(hashed, "correct horse battery staple") is False
    assert needs_rehash(hashed) is False


def test_same_password_hashes_differently_each_time() -> None:
    assert hash_password("same-password-123") != hash_password("same-password-123")


def test_unicode_passwords_are_normalised() -> None:
    # Full-width digits (NFKC-equivalent to ASCII digits) must verify the same.
    hashed = hash_password("পাসওয়ার্ড-১২৩৪-1234")
    full_width_1234 = "".join(chr(0xFF11 + offset) for offset in range(4))
    assert verify_password(hashed, "পাসওয়ার্ড-১২৩৪-" + full_width_1234) is True


def test_malformed_hash_never_verifies() -> None:
    assert verify_password("not-a-hash", "anything") is False
    assert needs_rehash("not-a-hash") is True


def test_dummy_verification_does_not_raise() -> None:
    verify_against_dummy("whatever")


@pytest.mark.parametrize(
    ("password", "issue"),
    [
        ("short", PasswordIssue.TOO_SHORT),
        ("x" * 129, PasswordIssue.TOO_LONG),
        ("aaaaaaaaaaaaaa", PasswordIssue.REPEATED_CHARACTER),
        ("Password1234", PasswordIssue.TOO_COMMON),
        ("CrescentFoundry", PasswordIssue.TOO_COMMON),
        ("my-EMP0042-is-my-password", PasswordIssue.CONTAINS_LOGIN_ID),
    ],
)
def test_password_policy_rejects(password: str, issue: str) -> None:
    assert issue in password_policy_issues(password, min_length=12, login_id="emp0042")


def test_password_policy_accepts_long_passphrases_without_composition_rules() -> None:
    assert password_policy_issues("molten iron pours at dawn", min_length=12, login_id="emp1") == []


# --- Tokens -----------------------------------------------------------------------


def test_session_tokens_are_random_and_stored_only_as_hashes() -> None:
    first, second = generate_session_token(), generate_session_token()

    assert first != second
    assert len(first) >= 43  # 32 bytes, base64url
    hashed = hash_session_token(first)
    assert len(hashed) == 64
    assert first not in hashed


def test_csrf_token_is_bound_to_session_and_secret() -> None:
    session_hash = hash_session_token(generate_session_token())
    token = csrf_token_for(SECRET, session_hash)

    assert csrf_token_matches(SECRET, session_hash, token) is True
    assert csrf_token_matches(SECRET, session_hash, token + "x") is False
    other_session = hash_session_token(generate_session_token())
    assert csrf_token_matches(SECRET, other_session, token) is False
    other_secret = SecretStr("another-secret-key-0123456789-abcdefghijklmnop")
    assert csrf_token_matches(other_secret, session_hash, token) is False


def test_keyed_digest_is_purpose_specific() -> None:
    assert keyed_digest(SECRET, "login-identifier", "emp1") != keyed_digest(
        SECRET, "login-ip", "emp1"
    )


# --- Identifiers ------------------------------------------------------------------


def test_uuid7_layout_and_ordering() -> None:
    first = uuid7()
    second = uuid7()

    assert first.version == 7
    assert first.variant == uuid.RFC_4122
    assert first != second
    # The 48-bit millisecond prefix makes later identifiers sort after earlier ones.
    assert (first.int >> 80) <= (second.int >> 80)


# --- Throttling state machine -------------------------------------------------------


def _state(
    count: int, started: datetime, locked: datetime | None, now: datetime
) -> tuple[int, datetime, datetime | None]:
    return next_failure_state(
        failure_count=count,
        window_started_at=started,
        locked_until=locked,
        now=now,
        max_failures=3,
        window=timedelta(minutes=15),
        lockout=timedelta(minutes=15),
    )


def test_throttle_locks_after_max_failures_in_window() -> None:
    now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)

    count, _started, locked = _state(2, now - timedelta(minutes=5), None, now)

    assert count == 3
    assert locked == now + timedelta(minutes=15)


def test_throttle_window_resets_after_expiry() -> None:
    now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)

    count, started, locked = _state(2, now - timedelta(minutes=16), None, now)

    assert (count, started, locked) == (1, now, None)


def test_throttle_resets_after_lockout_expires() -> None:
    now = datetime(2026, 11, 12, 10, 0, tzinfo=UTC)

    count, _, locked = _state(3, now - timedelta(minutes=5), now - timedelta(seconds=1), now)

    assert count == 1
    assert locked is None


# --- Column types -------------------------------------------------------------------


def test_utc_datetime_rejects_naive_values() -> None:
    column_type = UTCDateTime()
    with pytest.raises(ValueError, match="Naive datetimes"):
        column_type.process_bind_param(datetime(2026, 1, 1), None)  # type: ignore[arg-type]


def test_utc_datetime_round_trip() -> None:
    column_type = UTCDateTime()
    ist = datetime(2026, 1, 1, 15, 30, tzinfo=UTC) + timedelta(hours=0)
    stored = column_type.process_bind_param(ist, None)  # type: ignore[arg-type]
    assert stored is not None and stored.tzinfo is None
    loaded = column_type.process_result_value(stored, None)  # type: ignore[arg-type]
    assert loaded == ist and loaded is not None and loaded.tzinfo is UTC


def test_uuid_binary_round_trip() -> None:
    value = uuid7()
    column_type = UUIDBinary()
    stored = column_type.process_bind_param(value, None)  # type: ignore[arg-type]
    assert stored is not None and len(stored) == 16
    assert column_type.process_result_value(stored, None) == value  # type: ignore[arg-type]
