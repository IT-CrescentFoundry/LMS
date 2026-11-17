"""Import job lifecycle (Stage D): upload, mapping, validation, decisions, commit.

State machine (illegal transitions are refused with ``409 import_invalid_transition``)::

    uploaded -> mapping_required -> validating -> validation_failed | ready_for_approval
    validation_failed / ready_for_approval -> validating (re-validate)
    validation_failed / ready_for_approval -> mapping_required (re-map)
    ready_for_approval -> validation_failed (a row decision needs re-validation)
    ready_for_approval -> committing -> completed | completed_with_skips | failed
    any open state -> cancelled | expired

``validating`` and ``committing`` are held while the work runs: a second request for the
same job sees them and is refused, and commits are additionally serialised by the
``graph_lock`` row ``imports``. A job that is committed (or failed) can never be
committed again: re-importing the same workbook needs a new job, whose rows then match
existing records and are classified *unchanged* (idempotent re-import).

``committing`` is never visible to other requests: it is set and replaced inside the
one commit transaction. ``validating`` is committed (so a concurrent request is
refused); if the validating request dies, the job returns to ``mapping_required`` once
``import_validation_timeout_minutes`` have passed.

Expiry (``import_job_expiry_days`` after upload) is enforced by every state-changing
action, not only when a job is viewed. An uploaded file is *released* in the same
transaction as the job's final status and deleted only after that commit (see
``storage``); ``reconcile_storage`` expires overdue jobs, recovers abandoned
validations and removes orphan files on routine Import Control Room requests.
"""

import hashlib
import re
import uuid
from datetime import date, timedelta
from typing import Any

from openpyxl.utils import get_column_letter
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.audit import AuditOutcome
from app.models.imports import (
    ImportIssue,
    ImportJob,
    ImportRow,
    ImportStatus,
    ImportValueMapping,
    IssueSeverity,
    MappingStatus,
    ProvenanceAction,
    RecordProvenance,
    RowDecision,
    RowOutcome,
)
from app.models.organisation import GraphLock
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity.context import Actor
from app.services.imports import storage
from app.services.imports.employees_profile import (
    DomainContext,
    IssueDraft,
    StagedRow,
    check_within_file,
    load_existing,
    load_people_by_joining_date,
    parse,
    resolve_references,
    run_domain,
)
from app.services.imports.profiles import (
    FieldType,
    ProfileSpec,
    get_profile,
    is_excluded_header,
    normalise_label,
)
from app.services.imports.references import MODELS, ReferenceIndex
from app.services.imports.workbook import (
    Limits,
    _sheet_parts,
    check_file,
    inspect_workbook,
    malformed_workbook_as_422,
    open_workbook,
)
from app.services.organisation.support import audit

S = ImportStatus
TRANSITIONS: dict[str, frozenset[str]] = {
    S.UPLOADED: frozenset({S.MAPPING_REQUIRED, S.CANCELLED, S.EXPIRED}),
    S.MAPPING_REQUIRED: frozenset({S.MAPPING_REQUIRED, S.VALIDATING, S.CANCELLED, S.EXPIRED}),
    S.VALIDATING: frozenset({S.VALIDATION_FAILED, S.READY_FOR_APPROVAL, S.MAPPING_REQUIRED}),
    S.VALIDATION_FAILED: frozenset(
        {S.VALIDATING, S.MAPPING_REQUIRED, S.VALIDATION_FAILED, S.CANCELLED, S.EXPIRED}
    ),
    S.READY_FOR_APPROVAL: frozenset(
        {
            S.VALIDATING,
            S.MAPPING_REQUIRED,
            S.VALIDATION_FAILED,
            S.COMMITTING,
            S.CANCELLED,
            S.EXPIRED,
        }
    ),
    S.COMMITTING: frozenset({S.COMPLETED, S.COMPLETED_WITH_SKIPS, S.FAILED}),
}


def limits_of(settings: Settings) -> Limits:
    return Limits(
        max_upload_bytes=settings.import_max_upload_bytes,
        max_expanded_bytes=settings.import_max_expanded_bytes,
        max_zip_entries=settings.import_max_zip_entries,
        max_compression_ratio=settings.import_max_compression_ratio,
        max_sheets=settings.import_max_sheets,
        max_rows=settings.import_max_rows_per_sheet,
        max_columns=settings.import_max_columns,
        max_total_rows=settings.import_max_rows_total,
    )


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def transition(job: ImportJob, target: str) -> None:
    if not can_transition(job.status, target):
        raise AppError(
            409,
            "import_invalid_transition",
            f"This import cannot go from '{job.status}' to '{target}'.",
        )
    job.status = target


def profile_of(job: ImportJob) -> ProfileSpec:
    profile = get_profile(job.profile_code, job.profile_version)
    if profile is None:  # pragma: no cover - profile versions are never removed
        raise AppError(
            409, "import_profile_unavailable", "The import profile version is unavailable."
        )
    return profile


def safe_filename(raw: str | None) -> str:
    name = (raw or "").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "upload.xlsx"


def _job_audit(
    db: Session,
    actor: Actor,
    meta: RequestMeta,
    event: AuditEventType,
    job: ImportJob,
    **metadata: Any,
) -> None:
    audit(
        db,
        actor,
        meta,
        event,
        TargetType.IMPORT_JOB,
        job.public_id,
        {
            "profile": job.profile_code,
            "profile_version": job.profile_version,
            "status": job.status,
            **metadata,
        },
    )


def get_job(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> ImportJob:
    statement = select(ImportJob).where(ImportJob.public_id == public_id)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    job = db.scalars(statement).one_or_none()
    if job is None:
        raise AppError(404, "import_job_not_found", "Import job not found.")
    return job


def _reload(db: Session, job_id: int) -> ImportJob:
    job = db.get(ImportJob, job_id)
    if job is None:  # pragma: no cover - jobs are never deleted
        raise AppError(404, "import_job_not_found", "Import job not found.")
    return job


def ensure_version(job: ImportJob, version: int) -> None:
    if job.version != version:
        raise AppError(409, "version_conflict", "The import job was changed in the meantime.")


# ------------------------------------------------------------------------------ upload


def suggested_mapping(workbook: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = []
    for sheet in workbook:
        if sheet["suggested_section"] and sheet["header_row"] and sheet["state"] == "visible":
            columns = {
                str(h["index"]): h["suggested_field"]
                for h in sheet["headers"]
                if h["suggested_field"]
            }
            sections.append(
                {
                    "section": sheet["suggested_section"],
                    "sheet": sheet["name"],
                    "header_row": sheet["header_row"],
                    "columns": columns,
                }
            )
    return sections


def upload(
    db: Session,
    settings: Settings,
    *,
    actor: Actor,
    meta: RequestMeta,
    profile_code: str,
    filename: str,
    data: bytes,
) -> ImportJob:
    profile = get_profile(profile_code)
    if profile is None:
        raise AppError(404, "import_profile_not_found", "Import profile not found.")
    name = safe_filename(filename)
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        workbook = inspect_workbook(data, name, profile, limits_of(settings))
    except AppError as error:
        record_audit_event(
            db,
            event_type=AuditEventType.IMPORT_UPLOAD_REJECTED,
            outcome=AuditOutcome.FAILURE,
            meta=meta,
            actor_user_id=actor.user_id,
            metadata={
                "profile": profile_code,
                "code": error.code,
                "size": len(data),
                "sha256": sha256,
            },
        )
        db.commit()
        raise
    previous = db.scalars(
        select(ImportJob.public_id).where(
            ImportJob.profile_code == profile.code,
            ImportJob.file_sha256 == sha256,
            ImportJob.status.in_([S.COMPLETED, S.COMPLETED_WITH_SKIPS]),
        )
    ).all()
    job = ImportJob(
        profile_code=profile.code,
        profile_version=profile.version,
        status=S.UPLOADED,
        original_filename=name,
        file_sha256=sha256,
        file_size=len(data),
        file_stored=True,
        workbook=[{k: v for k, v in sheet.items() if k != "part"} for sheet in workbook],
        column_mapping=suggested_mapping(workbook),
        summary={
            "mapping_confirmed": False,
            "previously_imported_by": [str(p) for p in previous],
            "decisions": {},
        },
        uploaded_by_user_id=actor.user_id,
        uploaded_at=utcnow(),
    )
    db.add(job)
    db.flush()
    transition(job, S.MAPPING_REQUIRED)
    storage.save(settings, job.public_id, data)
    _job_audit(
        db,
        actor,
        meta,
        AuditEventType.IMPORT_UPLOADED,
        job,
        size=len(data),
        sha256=sha256,
        sheets=len(workbook),
    )
    return job


# Open states a job can expire from (``validating`` is recovered first; see below).
EXPIRABLE = frozenset({S.UPLOADED, S.MAPPING_REQUIRED, S.VALIDATION_FAILED, S.READY_FOR_APPROVAL})
# An orphan file younger than this may belong to an upload whose transaction is still
# in flight, so reconciliation leaves it alone.
ORPHAN_GRACE_SECONDS = 3600


def _expiry_due(settings: Settings, job: ImportJob) -> bool:
    return job.uploaded_at + timedelta(days=settings.import_job_expiry_days) <= utcnow()


def _validation_abandoned(settings: Settings, job: ImportJob) -> bool:
    timeout = timedelta(minutes=settings.import_validation_timeout_minutes)
    return job.status == S.VALIDATING and job.updated_at + timeout <= utcnow()


def refuse_if_expired(settings: Settings, job: ImportJob) -> None:
    """State-changing actions never act on an overdue job, even before it is marked."""
    if job.status == S.EXPIRED or (job.status in EXPIRABLE and _expiry_due(settings, job)):
        raise AppError(
            409, "import_job_expired", "This import has expired. Upload the workbook again."
        )


def housekeep_job(
    db: Session, settings: Settings, job: ImportJob, *, actor: Actor, meta: RequestMeta
) -> bool:
    """Recover an abandoned validation and expire an overdue job. True if changed."""
    changed = False
    if _validation_abandoned(settings, job):
        transition(job, S.MAPPING_REQUIRED)
        _job_audit(db, actor, meta, AuditEventType.IMPORT_VALIDATION_ABANDONED, job)
        changed = True
    if job.status in EXPIRABLE and _expiry_due(settings, job):
        transition(job, S.EXPIRED)
        job.finished_at = utcnow()
        _release_file(job)
        _job_audit(db, actor, meta, AuditEventType.IMPORT_EXPIRED, job)
        changed = True
    return changed


def _release_file(job: ImportJob) -> None:
    """Mark the upload as no longer needed, in the same transaction as the final status.

    No file-system work happens here: ``discard_released_file`` deletes the file only
    after the transaction commits, so a failed commit never leaves an open job without
    its workbook.
    """
    job.file_stored = False


def discard_released_file(settings: Settings, job: ImportJob) -> None:
    """After commit: delete a released upload (best effort; reconciliation retries)."""
    if not job.file_stored:
        storage.remove(settings, job.public_id)


def reconcile_storage(
    db: Session, settings: Settings, *, actor: Actor, meta: RequestMeta
) -> dict[str, int]:
    """Housekeeping on routine requests (no background worker; idempotent and retry-safe).

    1. Overdue jobs are expired and abandoned validations recovered (rows another
       request holds are skipped, not waited for); this is committed first.
    2. Then files are deleted when their job no longer holds them (finished or
       released), and - after a grace period, as an upload may still be in flight -
       files with no job and interrupted ``.part`` writes.

    A file is never deleted while the database records its job as holding it.
    """
    now = utcnow()
    result = {"expired": 0, "recovered": 0, "files_removed": 0}
    due = db.scalars(
        select(ImportJob)
        .where(
            or_(
                and_(
                    ImportJob.status.in_(sorted(EXPIRABLE)),
                    ImportJob.uploaded_at <= now - timedelta(days=settings.import_job_expiry_days),
                ),
                and_(
                    ImportJob.status == S.VALIDATING,
                    ImportJob.updated_at
                    <= now - timedelta(minutes=settings.import_validation_timeout_minutes),
                ),
            )
        )
        .with_for_update(skip_locked=True)
    ).all()
    for job in due:
        was_validating = job.status == S.VALIDATING
        if housekeep_job(db, settings, job, actor=actor, meta=meta):
            result["recovered"] += int(was_validating)
            result["expired"] += int(job.status == S.EXPIRED)
    db.commit()
    files = storage.stored_files(settings)
    ids = sorted({f.job_id for f in files if f.job_id is not None})
    states: dict[uuid.UUID, bool] = {}
    if ids:
        query = select(ImportJob.public_id, ImportJob.file_stored).where(
            ImportJob.public_id.in_(ids)
        )
        states = {public_id: stored for public_id, stored in db.execute(query)}
    for stored in files:
        if stored.job_id is None or (not stored.partial and states.get(stored.job_id)):
            continue  # not a name this module creates, or still held by its job
        orphan = stored.job_id not in states or stored.partial
        if orphan and stored.age_seconds < ORPHAN_GRACE_SECONDS:
            continue  # possibly an upload still in flight
        if storage.discard(stored):
            result["files_removed"] += 1
    return result


# ----------------------------------------------------------------------------- mapping


def set_mapping(
    db: Session,
    settings: Settings,
    job: ImportJob,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    sections: list[dict[str, Any]],
) -> ImportJob:
    ensure_version(job, version)
    refuse_if_expired(settings, job)
    profile = profile_of(job)
    if not can_transition(job.status, S.MAPPING_REQUIRED):
        transition(job, S.MAPPING_REQUIRED)  # raises the standard 409
    sheets = {sheet["name"]: sheet for sheet in job.workbook}
    if not sections:
        raise AppError(422, "import_mapping_empty", "Map at least one worksheet section.")
    seen: set[tuple[str, str]] = set()
    normalised = []
    for item in sections:
        kind, sheet_name, header_row = (
            str(item.get("section")),
            str(item.get("sheet")),
            item.get("header_row"),
        )
        if kind not in {s.kind for s in profile.sections}:
            raise AppError(422, "import_mapping_unknown_section", f"Unknown section {kind!r}.")
        if sheet_name not in sheets:
            raise AppError(
                422,
                "import_mapping_unknown_sheet",
                "The worksheet does not exist in this workbook.",
            )
        if (sheet_name, kind) in seen:
            raise AppError(
                422, "import_mapping_duplicate_section", "A worksheet section is mapped twice."
            )
        seen.add((sheet_name, kind))
        spec = profile.section(kind)
        inspected = sheets[sheet_name]
        # Only the header row detected at upload is accepted: every header in it was
        # checked against the protected exclusion list. Choosing another row is
        # deferred - it would let a data row stand in for the real headers (such as
        # "Aadhaar No") and so bypass the exclusion check.
        if inspected["header_row"] is None or header_row != inspected["header_row"]:
            raise AppError(
                422,
                "import_mapping_header_row",
                "The header row is detected automatically and cannot be changed.",
            )
        texts = {h["index"]: h["text"] for h in inspected["headers"]}
        columns: dict[str, str] = {}
        for raw_index, field_name in (item.get("columns") or {}).items():
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                raise AppError(
                    422, "import_mapping_unknown_column", "A mapped column has no header."
                ) from None
            if field_name not in spec.field_names:
                raise AppError(
                    422, "import_mapping_unknown_field", f"Unknown field {field_name!r}."
                )
            if field_name in columns.values():
                raise AppError(
                    422, "import_mapping_field_twice", f"Field {field_name!r} is mapped twice."
                )
            if index not in texts:
                raise AppError(
                    422, "import_mapping_unknown_column", "A mapped column has no header."
                )
            if is_excluded_header(texts[index]):
                raise AppError(
                    422,
                    "import_mapping_column_excluded",
                    "This column holds protected personal or pay data and cannot be imported.",
                )
            columns[str(index)] = field_name
        missing = [f.name for f in spec.fields if f.required and f.name not in columns.values()]
        if missing:
            raise AppError(
                422,
                "import_mapping_required_missing",
                f"Required fields are not mapped: {', '.join(missing)}.",
            )
        normalised.append(
            {
                "section": kind,
                "sheet": sheet_name,
                "header_row": header_row,
                "columns": columns,
                "letters": {index: get_column_letter(int(index)) for index in columns},
                "header_texts": {index: texts[int(index)] for index in columns},
            }
        )
    job.column_mapping = normalised
    job.summary = {**(job.summary or {}), "mapping_confirmed": True, "decisions": {}}
    transition(job, S.MAPPING_REQUIRED)
    _clear_staging(db, job)
    _job_audit(
        db,
        actor,
        meta,
        AuditEventType.IMPORT_MAPPING_SET,
        job,
        sections=[f"{s['sheet']}:{s['section']}" for s in normalised],
    )
    return job


def _clear_staging(db: Session, job: ImportJob) -> None:
    db.execute(delete(ImportIssue).where(ImportIssue.job_id == job.id))
    db.execute(delete(ImportRow).where(ImportRow.job_id == job.id))


# -------------------------------------------------------------------------- validation


def _row_key(section: str, sheet: str, number: int) -> str:
    return f"{section}|{sheet}|{number}"


def validate(
    db: Session,
    settings: Settings,
    job: ImportJob,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
) -> ImportJob:
    ensure_version(job, version)
    refuse_if_expired(settings, job)
    if not (job.summary or {}).get("mapping_confirmed"):
        raise AppError(409, "import_mapping_not_confirmed", "Confirm the column mapping first.")
    transition(job, S.VALIDATING)
    db.commit()  # visible to concurrent requests: a second validation or commit is refused
    job_id = job.id
    try:
        staged, parsed_counts, unresolved = _evaluate(
            db, settings, job, actor=actor, meta=meta, commit=False, apply_updates=False
        )
    except Exception:
        db.rollback()
        job = db.get(ImportJob, job_id) or job
        transition(job, S.MAPPING_REQUIRED)
        db.commit()
        raise
    db.rollback()  # the dry run never reaches the domain tables
    job = _reload(db, job_id)
    _write_staging(db, job, staged)
    _stage_pending_mappings(db, job, unresolved)
    summary = _summary(staged, parsed_counts)
    job.summary = {**(job.summary or {}), **summary}
    job.validated_at = utcnow()
    job.validated_by_user_id = actor.user_id
    ready = (
        summary["blocking_errors"] == 0
        and summary["undecided_duplicates"] == 0
        and summary["importable"] > 0
    )
    transition(job, S.READY_FOR_APPROVAL if ready else S.VALIDATION_FAILED)
    _job_audit(
        db,
        actor,
        meta,
        AuditEventType.IMPORT_VALIDATED,
        job,
        **{k: summary[k] for k in ("rows", "blocking_errors", "warnings")},
    )
    return job


def _evaluate(
    db: Session,
    settings: Settings,
    job: ImportJob,
    *,
    actor: Actor,
    meta: RequestMeta,
    commit: bool,
    apply_updates: bool,
    staged: list[StagedRow] | None = None,
) -> tuple[list[StagedRow], dict[str, int], dict[tuple[str, str], str]]:
    profile = profile_of(job)
    counts = {"skipped_blank": 0, "skipped_repeated_header": 0}
    if staged is None:
        data = storage.load(settings, job.public_id)
        archive = check_file(
            data,
            job.original_filename
            if job.original_filename.lower().endswith(".xlsx")
            else "upload.xlsx",
            limits_of(settings),
        )
        try:
            with malformed_workbook_as_422():
                parts = _sheet_parts(archive)
                workbook = open_workbook(data)
                try:
                    result = parse(
                        workbook,
                        archive,
                        parts,
                        job.column_mapping or [],
                        profile,
                        limits_of(settings),
                    )
                finally:
                    workbook.close()
        finally:
            archive.close()
        staged = result.rows
        counts = {
            "skipped_blank": result.skipped_blank,
            "skipped_repeated_header": result.skipped_repeated_header,
        }
        decisions = (job.summary or {}).get("decisions", {})
        for row in staged:
            if (
                decision := decisions.get(_row_key(row.section, row.sheet, row.row_number))
            ) is not None:
                row.decision = decision["decision"]
    existing = load_existing(db, staged)
    check_within_file(staged, profile, existing, load_people_by_joining_date(db, staged))
    index = ReferenceIndex.load(db)
    resolve_references(staged, index, profile)
    ctx = DomainContext(db, actor, meta, job.public_id, apply_updates, commit, index, existing)
    run_domain(ctx, staged, profile)
    return staged, counts, index.unresolved


def _write_staging(db: Session, job: ImportJob, staged: list[StagedRow]) -> None:
    _clear_staging(db, job)
    profile = profile_of(job)
    decisions = (job.summary or {}).get("decisions", {})
    for row in staged:
        record = ImportRow(
            job_id=job.id,
            section=row.section,
            sheet=row.sheet,
            row_number=row.row_number,
            natural_key=row.natural_key(profile.section(row.section)),
            values={
                k: (v.isoformat() if isinstance(v, date) else v) for k, v in row.values.items()
            },
            source=row.source,
            outcome=row.outcome,
            changes=row.changes,
            decision=row.decision,
            target_public_id=row.target_public_id,
        )
        if (decided := decisions.get(_row_key(row.section, row.sheet, row.row_number))) is not None:
            record.decision_reason = decided.get("reason")
            record.decided_by_user_id = decided.get("by")
        db.add(record)
        db.flush()
        for issue in row.issues:
            db.add(_issue(job, record, row, issue))


def _issue(
    job: ImportJob, record: ImportRow | None, row: StagedRow | None, issue: IssueDraft
) -> ImportIssue:
    return ImportIssue(
        job_id=job.id,
        row_id=record.id if record else None,
        section=row.section if row else None,
        sheet=row.sheet if row else None,
        row_number=row.row_number if row else None,
        column=issue.column,
        field=issue.field,
        code=issue.code,
        severity=issue.severity,
        source_value=issue.source_value,
        params=issue.params,
    )


def _summary(staged: list[StagedRow], counts: dict[str, int]) -> dict[str, Any]:
    by_section: dict[str, dict[str, int]] = {}
    for row in staged:
        bucket = by_section.setdefault(row.section, {o.value: 0 for o in RowOutcome})
        bucket[row.outcome] += 1
    # Explicitly skipped rows keep their issues for the record but never block approval.
    active = [row for row in staged if not row.skipped]
    errors = sum(1 for row in active for i in row.issues if i.severity == IssueSeverity.ERROR)
    warnings = sum(1 for row in active for i in row.issues if i.severity == IssueSeverity.WARNING)
    undecided = sum(
        1
        for row in active
        if row.decision is None
        and any((i.params or {}).get("requires_decision") for i in row.issues)
    )
    importable = sum(
        1
        for row in staged
        if row.outcome in (RowOutcome.NEW, RowOutcome.UPDATE, RowOutcome.UNCHANGED)
    )
    return {
        "rows": len(staged),
        "by_section": by_section,
        "blocking_errors": errors,
        "error_rows": sum(1 for row in staged if row.outcome == RowOutcome.ERROR),
        "warnings": warnings,
        "undecided_duplicates": undecided,
        "importable": importable,
        "skipped_rows": sum(1 for row in staged if row.outcome == RowOutcome.SKIPPED),
        **counts,
    }


def _stage_pending_mappings(
    db: Session, job: ImportJob, unresolved: dict[tuple[str, str], str]
) -> None:
    for (kind, normalised), text in unresolved.items():
        current = db.scalars(
            select(ImportValueMapping).where(
                ImportValueMapping.kind == kind,
                ImportValueMapping.normalised_text == normalised,
                ImportValueMapping.status != MappingStatus.SUPERSEDED,
            )
        ).first()
        if current is None:
            db.add(
                ImportValueMapping(
                    kind=kind,
                    source_text=text,
                    normalised_text=normalised,
                    status=MappingStatus.PENDING,
                    first_job_id=job.id,
                )
            )


# --------------------------------------------------------------------------- decisions


def decide_row(
    db: Session,
    settings: Settings,
    job: ImportJob,
    row_id: int,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    decision: str | None,
    reason: str | None,
) -> ImportJob:
    ensure_version(job, version)
    refuse_if_expired(settings, job)
    if job.status not in (S.VALIDATION_FAILED, S.READY_FOR_APPROVAL):
        raise AppError(
            409, "import_invalid_transition", "Rows can be decided only after validation."
        )
    row = db.scalars(
        select(ImportRow).where(ImportRow.id == row_id, ImportRow.job_id == job.id)
    ).one_or_none()
    if row is None:
        raise AppError(404, "import_row_not_found", "Import row not found.")
    if decision is not None and decision not in tuple(RowDecision):
        raise AppError(422, "import_decision_invalid", "Unknown decision.")
    if decision == RowDecision.SKIP and not (reason and reason.strip()):
        raise AppError(422, "import_skip_reason_required", "A reason is required to skip a row.")
    decisions = dict((job.summary or {}).get("decisions", {}))
    key = _row_key(row.section, row.sheet, row.row_number)
    if decision is None:
        decisions.pop(key, None)
    else:
        decisions[key] = {
            "decision": decision,
            "reason": (reason or "").strip()[:500] or None,
            "by": actor.user_id,
            "at": utcnow().isoformat(),
        }
    row.decision, row.decision_reason = decision, (reason or "").strip()[:500] or None
    row.decided_by_user_id, row.decided_at = actor.user_id, utcnow()
    job.summary = {**(job.summary or {}), "decisions": decisions}
    transition(job, S.VALIDATION_FAILED)  # decisions take effect on re-validation
    audit(
        db,
        actor,
        meta,
        AuditEventType.IMPORT_ROW_DECIDED,
        TargetType.IMPORT_JOB,
        job.public_id,
        {"sheet": row.sheet, "row": row.row_number, "section": row.section, "decision": decision},
    )
    return job


# ------------------------------------------------------------------------------ commit


def _staged_from_records(db: Session, job: ImportJob) -> list[StagedRow]:
    profile = profile_of(job)
    rows = []
    for record in db.scalars(
        select(ImportRow).where(ImportRow.job_id == job.id).order_by(ImportRow.id)
    ):
        spec = profile.section(record.section)
        values = dict(record.values)
        for item in spec.fields:
            if item.type == FieldType.DATE and isinstance(values.get(item.name), str):
                values[item.name] = date.fromisoformat(values[item.name])
        mapping = next(
            m
            for m in job.column_mapping or []
            if m["section"] == record.section and m["sheet"] == record.sheet
        )
        letters = {name: mapping["letters"][index] for index, name in mapping["columns"].items()}
        staged = StagedRow(
            record.section,
            record.sheet,
            record.row_number,
            values,
            dict(record.source),
            letters,
            decision=record.decision,
        )
        staged.record_id = record.id
        staged.approved = (record.outcome, record.changes)
        rows.append(staged)
    return rows


def commit(
    db: Session,
    settings: Settings,
    job_public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    apply_updates: bool,
) -> ImportJob:
    lock = db.scalars(
        select(GraphLock).where(GraphLock.name == "imports").with_for_update()
    ).one_or_none()
    if lock is None:  # pragma: no cover - seeded by migration 0010
        raise AppError(500, "import_lock_missing", "The import lock row is missing.")
    job = get_job(db, job_public_id, for_update=True)
    ensure_version(job, version)
    refuse_if_expired(settings, job)
    if job.status != S.READY_FOR_APPROVAL:
        raise AppError(
            409,
            "import_not_ready",
            "Only a validated import that is ready for approval can be committed.",
        )
    if (
        job.validated_at is None
        or job.validated_at + timedelta(hours=settings.import_preview_valid_hours) < utcnow()
    ):
        raise AppError(
            409, "import_preview_expired", "The preview is out of date. Validate the import again."
        )
    labels: set[str] = set()
    for values in db.scalars(select(ImportRow.values).where(ImportRow.job_id == job.id)):
        for name in ("unit", "designation", "grade", "level", "location"):
            if isinstance(values, dict) and values.get(name):
                labels.add(normalise_label(str(values[name])))
    changed = db.scalar(
        select(func.count())
        .select_from(ImportValueMapping)
        .where(
            ImportValueMapping.decided_at > job.validated_at,
            ImportValueMapping.normalised_text.in_(sorted(labels) or [""]),
        )
    )
    if changed:
        raise AppError(
            409,
            "import_revalidation_required",
            "Reference mappings changed after validation. Validate again.",
        )
    transition(job, S.COMMITTING)
    job_id = job.id
    staged = _staged_from_records(db, job)
    try:
        rows, _counts, _unresolved = _evaluate(
            db,
            settings,
            job,
            actor=actor,
            meta=meta,
            commit=True,
            apply_updates=apply_updates,
            staged=staged,
        )
        failed = [row for row in rows if row.blocked]
        if failed:
            raise _CommitRefusedError(failed)
    except _CommitRefusedError as refused:
        db.rollback()
        return _mark_failed(db, job_id, actor, meta, refused.rows)
    # The commit re-runs every rule against the current records. If a row would now
    # do something other than what the approver saw (e.g. an employee created on the
    # screens since validation turns "new" into an update with unseen changes),
    # nothing is written: the job stays ready and must be validated again.
    if any(row.approved is not None and (row.outcome, row.changes) != row.approved for row in rows):
        db.rollback()
        raise AppError(
            409,
            "import_records_changed",
            "Records changed after validation, so the preview no longer matches. "
            "Validate again before approving.",
        )
    _record_commit(db, job, rows, actor, apply_updates)
    _release_file(job)
    _job_audit(
        db,
        actor,
        meta,
        AuditEventType.IMPORT_COMMITTED,
        job,
        **(job.summary or {}).get("committed", {}),
    )
    return job


class _CommitRefusedError(Exception):
    def __init__(self, rows: list[StagedRow]) -> None:
        super().__init__("commit refused")
        self.rows = rows


def _mark_failed(
    db: Session,
    job_id: int,
    actor: Actor,
    meta: RequestMeta,
    rows: list[StagedRow],
) -> ImportJob:
    job = _reload(db, job_id)
    job.status = S.COMMITTING  # the committing state was rolled back with the domain writes
    transition(job, S.FAILED)
    job.failure_code = "commit_rule_failed"
    job.finished_at = utcnow()
    for row in rows:
        record = db.get(ImportRow, row.record_id) if row.record_id else None
        for issue in row.issues:
            if issue.severity == IssueSeverity.ERROR:
                db.add(
                    _issue(
                        job,
                        record,
                        row,
                        IssueDraft(
                            issue.code,
                            issue.severity,
                            issue.field,
                            issue.column,
                            issue.source_value,
                            {**(issue.params or {}), "phase": "commit"},
                        ),
                    )
                )
    _release_file(job)
    _job_audit(db, actor, meta, AuditEventType.IMPORT_COMMIT_FAILED, job, failed_rows=len(rows))
    return job


def _record_commit(
    db: Session, job: ImportJob, rows: list[StagedRow], actor: Actor, apply_updates: bool
) -> None:
    counts = {"created": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    for row in rows:
        record = db.get(ImportRow, row.record_id) if row.record_id else None
        if record is None:  # pragma: no cover - rows are locked with their job
            raise AppError(500, "import_row_missing", "A staged import row disappeared.")
        action: str | None = None
        if row.outcome == RowOutcome.NEW:
            action, counts["created"] = ProvenanceAction.CREATED, counts["created"] + 1
        elif row.outcome == RowOutcome.UPDATE and apply_updates:
            action, counts["updated"] = ProvenanceAction.UPDATED, counts["updated"] + 1
        elif row.outcome == RowOutcome.UNCHANGED:
            action, counts["unchanged"] = ProvenanceAction.UNCHANGED, counts["unchanged"] + 1
        else:
            counts["skipped"] += 1
        record.outcome = (
            row.outcome if row.outcome != RowOutcome.UPDATE or apply_updates else RowOutcome.SKIPPED
        )
        record.target_public_id = row.target_public_id
        if action is not None and row.target_public_id is not None:
            db.add(
                RecordProvenance(
                    job_id=job.id,
                    row_id=record.id,
                    target_type=_TARGETS[row.section],
                    target_public_id=row.target_public_id,
                    action=action,
                )
            )
    job.committed_by_user_id = actor.user_id
    job.committed_at = job.finished_at = utcnow()
    job.summary = {**(job.summary or {}), "committed": counts, "apply_updates": apply_updates}
    transition(job, S.COMPLETED_WITH_SKIPS if counts["skipped"] else S.COMPLETED)


_TARGETS = {
    "employees": "employee",
    "assignments": "employee_assignment",
    "reporting": "reporting_relationship",
}


# ------------------------------------------------------------------------------ cancel


def cancel(
    db: Session,
    job: ImportJob,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
) -> ImportJob:
    ensure_version(job, version)
    transition(job, S.CANCELLED)
    job.finished_at = utcnow()
    _release_file(job)
    _job_audit(db, actor, meta, AuditEventType.IMPORT_CANCELLED, job)
    return job


# ---------------------------------------------------------------------- value mappings


def get_mapping(db: Session, public_id: uuid.UUID) -> ImportValueMapping:
    mapping = db.scalars(
        select(ImportValueMapping)
        .where(ImportValueMapping.public_id == public_id)
        .with_for_update()
    ).one_or_none()
    if mapping is None:
        raise AppError(404, "import_mapping_not_found", "Mapping not found.")
    return mapping


def _mapping_audit(
    db: Session, actor: Actor, meta: RequestMeta, event: AuditEventType, mapping: ImportValueMapping
) -> None:
    audit(
        db,
        actor,
        meta,
        event,
        TargetType.IMPORT_VALUE_MAPPING,
        mapping.public_id,
        {
            "kind": mapping.kind,
            "status": mapping.status,
            "target": str(mapping.target_public_id) if mapping.target_public_id else None,
        },
    )


def approve_mapping(
    db: Session,
    mapping: ImportValueMapping,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    target_public_id: uuid.UUID,
    reason: str | None,
) -> ImportValueMapping:
    if mapping.version != version:
        raise AppError(409, "version_conflict", "The mapping was changed in the meantime.")
    if mapping.status not in (MappingStatus.PENDING, MappingStatus.REJECTED):
        raise AppError(
            409,
            "import_mapping_already_decided",
            "Only a pending or rejected mapping can be approved.",
        )
    model = MODELS[mapping.kind]
    target = db.scalars(select(model).where(model.public_id == target_public_id)).one_or_none()
    if target is None:
        raise AppError(422, "import_mapping_target_not_found", "The chosen record does not exist.")
    if getattr(target, "is_active", True) is False:
        raise AppError(422, "import_mapping_target_inactive", "The chosen record is not active.")
    mapping.status, mapping.target_public_id = MappingStatus.APPROVED, target_public_id
    mapping.decided_by_user_id, mapping.decided_at = actor.user_id, utcnow()
    mapping.decision_reason = (reason or "").strip()[:500] or None
    db.flush()
    _mapping_audit(db, actor, meta, AuditEventType.IMPORT_VALUE_MAPPING_APPROVED, mapping)
    return mapping


def reject_mapping(
    db: Session,
    mapping: ImportValueMapping,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
) -> ImportValueMapping:
    if mapping.version != version:
        raise AppError(409, "version_conflict", "The mapping was changed in the meantime.")
    if mapping.status != MappingStatus.PENDING:
        raise AppError(
            409, "import_mapping_already_decided", "Only a pending mapping can be rejected."
        )
    mapping.status = MappingStatus.REJECTED
    mapping.decided_by_user_id, mapping.decided_at = actor.user_id, utcnow()
    mapping.decision_reason = (reason or "").strip()[:500] or None
    db.flush()
    _mapping_audit(db, actor, meta, AuditEventType.IMPORT_VALUE_MAPPING_REJECTED, mapping)
    return mapping


def supersede_mapping(
    db: Session,
    mapping: ImportValueMapping,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
) -> ImportValueMapping:
    """Withdraw a decision: it is kept as history and the label returns to the queue."""
    if mapping.version != version:
        raise AppError(409, "version_conflict", "The mapping was changed in the meantime.")
    if mapping.status not in (MappingStatus.APPROVED, MappingStatus.REJECTED):
        raise AppError(
            409, "import_mapping_not_decided", "Only a decided mapping can be withdrawn."
        )
    mapping.status = MappingStatus.SUPERSEDED
    mapping.decided_by_user_id, mapping.decided_at = actor.user_id, utcnow()
    mapping.decision_reason = (reason or "").strip()[:500] or mapping.decision_reason
    db.flush()
    replacement = ImportValueMapping(
        kind=mapping.kind,
        source_text=mapping.source_text,
        normalised_text=mapping.normalised_text,
        status=MappingStatus.PENDING,
        first_job_id=mapping.first_job_id,
    )
    db.add(replacement)
    db.flush()
    _mapping_audit(db, actor, meta, AuditEventType.IMPORT_VALUE_MAPPING_SUPERSEDED, mapping)
    return replacement
