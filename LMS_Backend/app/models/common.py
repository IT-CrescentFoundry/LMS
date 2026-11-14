"""Column mixins and constants shared by the Stage C organisation models.

Effective-dated rows use half-open periods ``[effective_from, effective_to)``.
``effective_from`` may be NULL for structure records whose start was never
recorded (treated as "since the earliest date"); ``effective_to`` NULL means
open-ended. History is preserved: business changes close rows and open new ones.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.ids import uuid7
from app.db.types import BigIntKey, UTCDateTime, UUIDBinary, utcnow

# Additional display-name languages; the stored name is canonical (English or as supplied).
TRANSLATION_LOCALES = ("bn", "hi", "gu")
TranslationLocale = Literal["bn", "hi", "gu"]
LOCALE_CHECK = "locale IN ('bn', 'hi', 'gu')"
PERIOD_CHECK = "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from"
OPEN_FLAG = "IF(effective_to IS NULL, 1, NULL)"


class PublicIdMixin:
    """Non-enumerable identifier exposed by the API (ADR-049)."""

    public_id: Mapped[uuid.UUID] = mapped_column(UUIDBinary(), unique=True, default=uuid7)


class TrackedMixin:
    """Who/when columns plus an optimistic-locking version (corrections need it)."""

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer)

    # declared_attr methods receive the mapped class, hence ``cls``.
    @declared_attr
    def created_by_user_id(cls) -> Mapped[int | None]:  # noqa: N805
        return mapped_column(BigIntKey, ForeignKey("user_account.id"))

    @declared_attr
    def updated_by_user_id(cls) -> Mapped[int | None]:  # noqa: N805
        return mapped_column(BigIntKey, ForeignKey("user_account.id"))

    @declared_attr.directive
    def __mapper_args__(cls) -> dict[str, Any]:  # noqa: N805
        return {"version_id_col": cls.__table__.c.version}  # type: ignore[attr-defined]
