"""Custom column types shared by all models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, Dialect, LargeBinary
from sqlalchemy.dialects import mysql
from sqlalchemy.types import TypeDecorator, TypeEngine

# BIGINT UNSIGNED on MySQL (primary and foreign keys must use the same type).
BigIntKey = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timestamp stored as naive UTC ``DATETIME(6)``, returned as aware UTC.

    Naive datetimes are rejected on write, so local-time values can never be
    stored by mistake.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[datetime]:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.DATETIME(fsp=6))
        return dialect.type_descriptor(DateTime())

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; use timezone-aware UTC values.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class UUIDBinary(TypeDecorator[uuid.UUID]):
    """UUID stored compactly as ``BINARY(16)``."""

    impl = LargeBinary
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[bytes]:
        if dialect.name == "mysql":
            return dialect.type_descriptor(mysql.BINARY(16))
        return dialect.type_descriptor(LargeBinary(16))

    def process_bind_param(self, value: uuid.UUID | None, dialect: Dialect) -> bytes | None:
        return None if value is None else value.bytes

    def process_result_value(self, value: bytes | None, dialect: Dialect) -> uuid.UUID | None:
        return None if value is None else uuid.UUID(bytes=bytes(value))
