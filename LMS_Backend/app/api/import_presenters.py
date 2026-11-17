"""Import API presenters (Stage D)."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import UserAccount
from app.models.imports import ImportIssue, ImportJob, ImportRow, ImportValueMapping, MappingStatus
from app.schemas.audit import AuditActorOut
from app.schemas.imports import (
    HeaderOut,
    ImportJobOut,
    ImportJobSummary,
    ImportProfileOut,
    IssueOut,
    MappingSectionOut,
    ProfileFieldOut,
    ProfileSectionOut,
    RowOut,
    SheetOut,
    SuggestionOut,
    ValueMappingOut,
)
from app.schemas.organisation import RefOut
from app.services.imports.profiles import ProfileSpec
from app.services.imports.references import MODELS, ReferenceIndex, label_of

COUNT_KEYS = (
    "rows",
    "blocking_errors",
    "error_rows",
    "warnings",
    "undecided_duplicates",
    "importable",
    "skipped_rows",
    "skipped_blank",
    "skipped_repeated_header",
    "by_section",
    "committed",
)


def actors(db: Session, ids: Sequence[int | None]) -> dict[int, AuditActorOut]:
    wanted = {i for i in ids if i}
    if not wanted:
        return {}
    return {
        user.id: AuditActorOut(
            public_id=user.public_id, login_id=user.login_id, display_name=user.display_name
        )
        for user in db.scalars(select(UserAccount).where(UserAccount.id.in_(sorted(wanted))))
    }


def profile_out(profile: ProfileSpec, permissions: frozenset[str]) -> ImportProfileOut:
    return ImportProfileOut(
        code=profile.code,
        version=profile.version,
        commit_mode=profile.commit_mode,
        can_run=f"imports.{profile.code}.run" in permissions,
        can_commit=f"imports.{profile.code}.commit" in permissions,
        sections=[
            ProfileSectionOut(
                kind=section.kind,
                sheet_aliases=list(section.sheet_aliases),
                natural_key=list(section.natural_key),
                fields=[
                    ProfileFieldOut(
                        name=spec.name,
                        type=str(spec.type),
                        required=spec.required,
                        aliases=list(spec.aliases),
                        reference=str(spec.reference) if spec.reference else None,
                    )
                    for spec in section.fields
                ],
            )
            for section in profile.sections
        ],
    )


def _counts(job: ImportJob) -> dict[str, Any]:
    summary = job.summary or {}
    return {key: summary[key] for key in COUNT_KEYS if key in summary}


def job_summary(job: ImportJob, people: dict[int, AuditActorOut]) -> ImportJobSummary:
    return ImportJobSummary(
        public_id=job.public_id,
        profile_code=job.profile_code,
        profile_version=job.profile_version,
        status=job.status,
        original_filename=job.original_filename,
        file_size=job.file_size,
        uploaded_by=people.get(job.uploaded_by_user_id),
        uploaded_at=job.uploaded_at,
        validated_at=job.validated_at,
        committed_at=job.committed_at,
        finished_at=job.finished_at,
        counts=_counts(job),
    )


def job_summaries(db: Session, jobs: Sequence[ImportJob]) -> list[ImportJobSummary]:
    people = actors(db, [job.uploaded_by_user_id for job in jobs])
    return [job_summary(job, people) for job in jobs]


def job_out(db: Session, job: ImportJob) -> ImportJobOut:
    people = actors(
        db, [job.uploaded_by_user_id, job.validated_by_user_id, job.committed_by_user_id]
    )
    base = job_summary(job, people)
    summary = job.summary or {}
    return ImportJobOut(
        **base.model_dump(),
        file_sha256=job.file_sha256,
        file_stored=job.file_stored,
        workbook=[
            SheetOut(
                name=sheet["name"],
                state=sheet["state"],
                dimensions=sheet.get("dimensions"),
                suggested_section=sheet.get("suggested_section"),
                header_row=sheet.get("header_row"),
                headers=[HeaderOut(**header) for header in sheet.get("headers", [])],
            )
            for sheet in job.workbook
        ],
        column_mapping=[
            MappingSectionOut(
                section=m["section"],
                sheet=m["sheet"],
                header_row=m["header_row"],
                columns=m["columns"],
            )
            for m in job.column_mapping or []
        ],
        mapping_confirmed=bool(summary.get("mapping_confirmed")),
        previously_imported_by=[uuid.UUID(p) for p in summary.get("previously_imported_by", [])],
        failure_code=job.failure_code,
        validated_by=people.get(job.validated_by_user_id or 0),
        committed_by=people.get(job.committed_by_user_id or 0),
        version=job.version,
    )


def issue_out(issue: ImportIssue) -> IssueOut:
    return IssueOut(
        id=issue.id,
        section=issue.section,
        sheet=issue.sheet,
        row_number=issue.row_number,
        column=issue.column,
        field=issue.field,
        code=issue.code,
        severity=issue.severity,  # type: ignore[arg-type]
        source_value=issue.source_value,
        params=issue.params,
    )


def rows_out(db: Session, rows: Sequence[ImportRow]) -> list[RowOut]:
    ids = [row.id for row in rows]
    by_row: dict[int, list[IssueOut]] = {row_id: [] for row_id in ids}
    if ids:
        for issue in db.scalars(
            select(ImportIssue).where(ImportIssue.row_id.in_(ids)).order_by(ImportIssue.id)
        ):
            if issue.row_id is not None:
                by_row[issue.row_id].append(issue_out(issue))
    return [
        RowOut(
            id=row.id,
            section=row.section,
            sheet=row.sheet,
            row_number=row.row_number,
            outcome=row.outcome,
            values=row.values,
            source=row.source,
            changes=row.changes,
            decision=row.decision,
            decision_reason=row.decision_reason,
            target_public_id=row.target_public_id,
            issues=by_row[row.id],
        )
        for row in rows
    ]


def mappings_out(db: Session, mappings: Sequence[ImportValueMapping]) -> list[ValueMappingOut]:
    index = (
        ReferenceIndex.load(db)
        if any(m.status == MappingStatus.PENDING for m in mappings)
        else None
    )
    people = actors(db, [m.decided_by_user_id for m in mappings])
    result = []
    for mapping in mappings:
        target = None
        if mapping.target_public_id is not None:
            model = MODELS[mapping.kind]
            record = db.scalars(
                select(model).where(model.public_id == mapping.target_public_id)
            ).one_or_none()
            if record is not None:
                target = RefOut(
                    public_id=record.public_id,
                    code=record.code,
                    name=label_of(mapping.kind, record),
                )
        suggestions = (
            [SuggestionOut(**s.__dict__) for s in index.suggest(mapping.kind, mapping.source_text)]
            if index is not None and mapping.status == MappingStatus.PENDING
            else []
        )
        result.append(
            ValueMappingOut(
                public_id=mapping.public_id,
                kind=mapping.kind,
                source_text=mapping.source_text,
                normalised_text=mapping.normalised_text,
                status=mapping.status,
                target=target,
                decision_reason=mapping.decision_reason,
                decided_by=people.get(mapping.decided_by_user_id or 0),
                decided_at=mapping.decided_at,
                created_at=mapping.created_at,
                suggestions=suggestions,
                version=mapping.version,
            )
        )
    return result
