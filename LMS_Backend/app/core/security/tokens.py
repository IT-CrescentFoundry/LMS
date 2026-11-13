"""Random tokens and HMAC-derived values.

* Session tokens are 256-bit random values sent only in an HttpOnly cookie. The
  database stores their SHA-256 hash, so a database read does not reveal usable
  session tokens. (A fast hash is appropriate: the input is high-entropy.)
* CSRF tokens are derived as HMAC-SHA256(secret key, session-token hash). They are
  bound to the session, never stored, and can be recomputed on page refresh.
* Throttle keys are HMACs of the submitted login identifier / client IP, so the
  throttle table holds no raw identifiers.
"""

import base64
import hashlib
import hmac
import secrets

from pydantic import SecretStr

SESSION_TOKEN_BYTES = 32


def generate_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def keyed_digest(secret_key: SecretStr, purpose: str, value: str) -> str:
    """Hex HMAC-SHA256 of ``value`` under a purpose-specific label."""
    message = f"{purpose}\x00{value}".encode()
    key = secret_key.get_secret_value().encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def csrf_token_for(secret_key: SecretStr, session_token_hash: str) -> str:
    digest = bytes.fromhex(keyed_digest(secret_key, "csrf", session_token_hash))
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def csrf_token_matches(secret_key: SecretStr, session_token_hash: str, candidate: str) -> bool:
    expected = csrf_token_for(secret_key, session_token_hash)
    return hmac.compare_digest(expected.encode("ascii"), candidate.encode("utf-8"))
