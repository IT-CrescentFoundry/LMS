"""Database-backed login throttling.

Counters live in MySQL (``login_throttle``) and are updated under a row lock
(``SELECT … FOR UPDATE`` after an atomic ``INSERT … ON DUPLICATE KEY UPDATE``), so
limits hold across multiple API processes and servers without extra
infrastructure. Two independent scopes are tracked:

* **identifier** — HMAC of the submitted login ID (applies equally to IDs that do
  not exist, so throttling never reveals whether an account exists);
* **ip** — HMAC of the client IP (slows password spraying across many accounts).

Throttle state is temporary and separate from the permanent account status.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security.tokens import keyed_digest
from app.models.identity import LoginThrottle, ThrottleScope


@dataclass(frozen=True)
class ThrottleKeys:
    identifier: str
    ip: str


def throttle_keys(
    settings: Settings, *, purpose: str, identifier: str, ip: str | None
) -> ThrottleKeys:
    return ThrottleKeys(
        identifier=keyed_digest(
            settings.secret_key, f"{purpose}-identifier", identifier.strip().casefold()
        ),
        ip=keyed_digest(settings.secret_key, f"{purpose}-ip", ip or "unknown"),
    )


def next_failure_state(
    *,
    failure_count: int,
    window_started_at: datetime,
    locked_until: datetime | None,
    now: datetime,
    max_failures: int,
    window: timedelta,
    lockout: timedelta,
) -> tuple[int, datetime, datetime | None]:
    """Pure state transition for one more failure: (count, window start, locked until)."""
    lock_expired = locked_until is not None and locked_until <= now
    if now - window_started_at >= window or lock_expired:
        failure_count, window_started_at, locked_until = 0, now, None
    failure_count += 1
    if failure_count >= max_failures:
        locked_until = now + lockout
    return failure_count, window_started_at, locked_until


def is_throttled(db: Session, keys: ThrottleKeys, now: datetime) -> bool:
    rows = db.scalars(
        select(LoginThrottle).where(
            (
                (LoginThrottle.scope == ThrottleScope.IDENTIFIER)
                & (LoginThrottle.key_hash == keys.identifier)
            )
            | ((LoginThrottle.scope == ThrottleScope.IP) & (LoginThrottle.key_hash == keys.ip))
        )
    ).all()
    return any(row.locked_until is not None and row.locked_until > now for row in rows)


def _locked_row(db: Session, scope: ThrottleScope, key_hash: str, now: datetime) -> LoginThrottle:
    insert_stmt = mysql_insert(LoginThrottle).values(
        scope=scope.value, key_hash=key_hash, failure_count=0, window_started_at=now
    )
    db.execute(insert_stmt.on_duplicate_key_update(key_hash=insert_stmt.inserted.key_hash))
    return db.scalars(
        select(LoginThrottle)
        .where(LoginThrottle.scope == scope.value, LoginThrottle.key_hash == key_hash)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def register_failure(db: Session, settings: Settings, keys: ThrottleKeys, now: datetime) -> None:
    window = timedelta(minutes=settings.login_failure_window_minutes)
    lockout = timedelta(minutes=settings.login_lockout_minutes)
    for scope, key_hash, max_failures in (
        (ThrottleScope.IDENTIFIER, keys.identifier, settings.login_max_failures_per_identifier),
        (ThrottleScope.IP, keys.ip, settings.login_max_failures_per_ip),
    ):
        row = _locked_row(db, scope, key_hash, now)
        row.failure_count, row.window_started_at, row.locked_until = next_failure_state(
            failure_count=row.failure_count,
            window_started_at=row.window_started_at,
            locked_until=row.locked_until,
            now=now,
            max_failures=max_failures,
            window=window,
            lockout=lockout,
        )
        row.last_failure_at = now


def reset_identifier(db: Session, keys: ThrottleKeys) -> None:
    """Clear the identifier counter after a successful login.

    The IP counter is deliberately *not* reset: otherwise an attacker holding one
    valid account could reset it between guesses against other accounts.
    """
    db.execute(
        delete(LoginThrottle).where(
            LoginThrottle.scope == ThrottleScope.IDENTIFIER,
            LoginThrottle.key_hash == keys.identifier,
        )
    )
