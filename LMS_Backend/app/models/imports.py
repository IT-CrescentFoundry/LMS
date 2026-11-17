"""Import framework models (Stage D, migration 0010).

* ``import_job`` - one uploaded workbook and its lifecycle (state machine in
  ``app.services.imports.jobs``). Stores file metadata and SHA-256, never the file.
* ``import_row`` - one staged source row of a mapped section: only *mapped* fields
  (normalised values and their source text); excluded columns are never read.
* ``import_issue`` - a file-, row- or cell-level error or warning.
* ``import_value_mapping`` - a reviewed decision that a source label (e.g. a
  designation spelling) means an existing canonical record. ``pending`` rows are the
  review queue; approved decisions are never edited, only superseded. Mappings never
  create canonical records.
* ``record_provenance`` - which import row created, updated or confirmed a business
  record (file, sheet and row are reachable through the row and job).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, UUIDBinary, utcnow
from app.models.common import PublicIdMixin


class ImportStatus(StrEnum):
    UPLOADED = "uploaded"
    MAPPING_REQUIRED = "mapping_required"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    READY_FOR_APPROVAL = "ready_for_approval"
    COMMITTING = "committing"
    COMPLETED = "completed"
    COMPLETED_WITH_SKIPS = "completed_with_skips"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = frozenset(
    {
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_SKIPS,
        ImportStatus.FAILED,
        ImportStatus.EXPIRED,
        ImportStatus.CANCELLED,
    }
)


class RowOutcome(StrEnum):
    NEW = "new"
    UPDATE = "update"
    UNCHANGED = "unchanged"
    ERROR = "error"
    SKIPPED = "skipped"


class RowDecision(StrEnum):
    SKIP = "skip"
    DISTINCT = "distinct"  # probable duplicate confirmed to be a different person


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class MappingKind(StrEnum):
    ORG_UNIT = "org_unit"
    DESIGNATION = "designation"
    LOCATION = "location"
    GRADE = "grade"
    JOB_LEVEL = "job_level"


class MappingStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ProvenanceAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


def _in(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(item.value) for item in values)})"


class ImportJob(PublicIdMixin, Base):
    __tablename__ = "import_job"
    __table_args__ = (
        CheckConstraint(_in("status", ImportStatus), name="status_valid"),
        CheckConstraint("file_size > 0", name="file_size_positive"),
        Index("ix_import_job_status", "status"),
        Index("ix_import_job_profile_sha", "profile_code", "file_sha256"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    profile_code: Mapped[str] = mapped_column(String(50))
    profile_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_stored: Mapped[bool] = mapped_column(Boolean, default=True)
    workbook: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    column_mapping: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    failure_code: Mapped[str | None] = mapped_column(String(80))
    uploaded_by_user_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    uploaded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    validated_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    committed_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )
    committed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 - SQLAlchemy mapper config


class ImportRow(Base):
    __tablename__ = "import_row"
    __table_args__ = (
        UniqueConstraint("job_id", "section", "sheet", "row_number"),
        CheckConstraint(_in("outcome", RowOutcome), name="outcome_valid"),
        CheckConstraint(
            f"decision IS NULL OR {_in('decision', RowDecision)}", name="decision_valid"
        ),
        Index("ix_import_row_job_outcome", "job_id", "outcome"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("import_job.id"))
    section: Mapped[str] = mapped_column(String(30))
    sheet: Mapped[str] = mapped_column(String(100))
    row_number: Mapped[int] = mapped_column(Integer)
    natural_key: Mapped[str] = mapped_column(String(400))
    values: Mapped[dict[str, Any]] = mapped_column(JSON)
    source: Mapped[dict[str, Any]] = mapped_column(JSON)
    outcome: Mapped[str] = mapped_column(String(20))
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    decision: Mapped[str | None] = mapped_column(String(20))
    decision_reason: Mapped[str | None] = mapped_column(String(500))
    decided_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    target_public_id: Mapped[uuid.UUID | None] = mapped_column(UUIDBinary())


class ImportIssue(Base):
    __tablename__ = "import_issue"
    __table_args__ = (
        CheckConstraint(_in("severity", IssueSeverity), name="severity_valid"),
        Index("ix_import_issue_job_severity", "job_id", "severity"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("import_job.id"))
    row_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("import_row.id"))
    section: Mapped[str | None] = mapped_column(String(30))
    sheet: Mapped[str | None] = mapped_column(String(100))
    row_number: Mapped[int | None] = mapped_column(Integer)
    column: Mapped[str | None] = mapped_column(String(10))
    field: Mapped[str | None] = mapped_column(String(50))
    code: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(10))
    source_value: Mapped[str | None] = mapped_column(String(200))
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ImportValueMapping(PublicIdMixin, Base):
    __tablename__ = "import_value_mapping"
    __table_args__ = (
        CheckConstraint(_in("kind", MappingKind), name="kind_valid"),
        CheckConstraint(_in("status", MappingStatus), name="status_valid"),
        CheckConstraint(
            "status <> 'approved' OR target_public_id IS NOT NULL", name="approved_has_target"
        ),
        CheckConstraint(
            "status <> 'pending' OR target_public_id IS NULL", name="pending_has_no_target"
        ),
        UniqueConstraint("kind", "normalised_text", "current_flag"),
        Index("ix_import_value_mapping_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(30))
    source_text: Mapped[str] = mapped_column(String(200))
    normalised_text: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    target_public_id: Mapped[uuid.UUID | None] = mapped_column(UUIDBinary())
    decision_reason: Mapped[str | None] = mapped_column(String(500))
    decided_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    first_job_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("import_job.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    # At most one current (non-superseded) decision per kind and normalised label.
    current_flag: Mapped[int | None] = mapped_column(
        Integer, Computed("IF(status <> 'superseded', 1, NULL)", persisted=True)
    )
    version: Mapped[int] = mapped_column(Integer)

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 - SQLAlchemy mapper config


class RecordProvenance(Base):
    __tablename__ = "record_provenance"
    __table_args__ = (
        CheckConstraint(_in("action", ProvenanceAction), name="action_valid"),
        Index("ix_record_provenance_target", "target_type", "target_public_id"),
        Index("ix_record_provenance_job", "job_id"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("import_job.id"))
    row_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("import_row.id"))
    target_type: Mapped[str] = mapped_column(String(40))
    target_public_id: Mapped[uuid.UUID] = mapped_column(UUIDBinary())
    action: Mapped[str] = mapped_column(String(20))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
