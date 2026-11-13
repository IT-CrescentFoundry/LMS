"""Password hashing (Argon2id) and password policy.

* Hashing uses ``argon2-cffi``'s :class:`PasswordHasher`, whose defaults are the
  RFC 9106 low-memory Argon2id profile (t=3, m=64 MiB, p=4). Hashes are
  self-describing, so parameters can be raised later; ``needs_rehash`` lets
  successful logins upgrade old hashes transparently.
* Passwords are NFKC-normalised before hashing and verification, so visually
  identical Unicode input (e.g. from different Indic keyboards) is treated alike.
* The policy follows NIST SP 800-63B: a minimum length, a maximum length, no
  composition rules, and rejection of commonly used and context-specific values.
* Plain-text passwords are never stored, logged or returned.
"""

import unicodedata
from functools import lru_cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MAX_PASSWORD_LENGTH = 128

_hasher = PasswordHasher()

# Exact matches (case-insensitive) that are rejected regardless of length.
_COMMON_PASSWORDS = frozenset(
    {
        "123456789012",
        "1234567890123",
        "12345678901234",
        "123456123456",
        "1q2w3e4r5t6y",
        "abcdefghijkl",
        "abc123abc123",
        "administrator",
        "admin12345678",
        "changeme1234",
        "crescent1234",
        "crescentfoundry",
        "crescentfoundry1",
        "crescentlms123",
        "foundry12345",
        "iloveyou1234",
        "letmein12345",
        "password1234",
        "password12345",
        "passwordpassword",
        "p@ssw0rd1234",
        "qwerty123456",
        "qwertyuiopas",
        "qwertyuiop123",
        "welcome12345",
        "welcome@1234",
        "zaq12wsxcde3",
    }
)


class PasswordIssue:
    """Stable policy violation codes (translated by the frontend)."""

    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"
    CONTAINS_LOGIN_ID = "contains_login_id"
    REPEATED_CHARACTER = "repeated_character"
    TOO_COMMON = "too_common"
    SAME_AS_CURRENT = "same_as_current"


def normalise_password(password: str) -> str:
    return unicodedata.normalize("NFKC", password)


def hash_password(password: str) -> str:
    return _hasher.hash(normalise_password(password))


def verify_password(password_hash: str, password: str) -> bool:
    """Constant-time verification. Returns False for any mismatch or malformed hash."""
    try:
        return _hasher.verify(password_hash, normalise_password(password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _hasher.hash("dummy-password-for-timing-equalisation")


def verify_against_dummy(password: str) -> None:
    """Spend the same time as a real verification (unknown account / no password)."""
    verify_password(_dummy_hash(), password)


def password_policy_issues(
    password: str, *, min_length: int, login_id: str | None = None
) -> list[str]:
    """Return policy violation codes; an empty list means the password is acceptable."""
    normalised = normalise_password(password)
    issues: list[str] = []
    if len(normalised) < min_length:
        issues.append(PasswordIssue.TOO_SHORT)
    if len(normalised) > MAX_PASSWORD_LENGTH:
        issues.append(PasswordIssue.TOO_LONG)
    folded = normalised.casefold()
    if login_id and len(login_id) >= 3 and login_id.strip().casefold() in folded:
        issues.append(PasswordIssue.CONTAINS_LOGIN_ID)
    if normalised and len(set(normalised)) == 1:
        issues.append(PasswordIssue.REPEATED_CHARACTER)
    if folded in _COMMON_PASSWORDS:
        issues.append(PasswordIssue.TOO_COMMON)
    return issues
