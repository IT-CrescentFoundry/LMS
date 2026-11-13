"""Public identifiers.

Records exposed outside the database carry a non-sequential ``public_id`` so that
API identifiers reveal neither row counts nor creation order of unrelated records.
UUIDv7 (RFC 9562) is used because its time-ordered prefix keeps B-tree index
inserts efficient. Python 3.12/3.13 have no built-in ``uuid7``, hence this helper.
"""

import secrets
import time
import uuid

_TIMESTAMP_MASK = (1 << 48) - 1
_RAND_A_MASK = (1 << 12) - 1
_RAND_B_MASK = (1 << 62) - 1


def uuid7() -> uuid.UUID:
    """Return a version-7 UUID: 48-bit Unix milliseconds + 74 random bits."""
    unix_ms = time.time_ns() // 1_000_000
    random_bits = int.from_bytes(secrets.token_bytes(10), "big")
    value = (unix_ms & _TIMESTAMP_MASK) << 80
    value |= 0x7 << 76  # version
    value |= ((random_bits >> 62) & _RAND_A_MASK) << 64  # rand_a
    value |= 0b10 << 62  # RFC 9562 variant
    value |= random_bits & _RAND_B_MASK  # rand_b
    return uuid.UUID(int=value)
