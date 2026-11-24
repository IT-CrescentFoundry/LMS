"""Import Control Room API (Stage D): ``/api/v1/imports``.

Permissions (migration 0010; HR Admin and Super Admin): ``imports.view`` for every read;
``imports.<profile>.run`` to upload, map, validate, decide rows and cancel;
``imports.<profile>.commit`` **plus the domain permissions the commit writes with**
(``employees.manage`` and ``reporting_lines.manage`` for profile ``employees``) to commit;
``imports.mappings.manage`` to approve, reject or withdraw reference mappings. Every
state-changing request needs the CSRF token. Import jobs are a shared administrative
workspace: any holder of the permissions above may act on any job, and every action
records who did it.

Uploaded files are deleted only after the transaction that finishes their job has
committed; listing jobs also runs the storage housekeeping (``jobs.reconcile_storage``).

The upload body is the raw ``.xlsx`` file (``Content-Type`` the OOXML spreadsheet type
or ``application/octet-stream``); its display name travels in ``X-File-Name``
(percent-encoded). The body is read up to the configured limit and never parsed as a
form.
"""

import uuid
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import select

from app.api.admin_support import audit_denials
from app.api.deps import DbSessionDep, RequestMetaDep, SettingsDep, require_permission
from app.api.import_presenters import (
    issue_out,
    job_out,
    job_summaries,
    mappings_out,
    profile_out,
    rows_out,
)
from app.core.errors import AppError
from app.models.imports import (
    ImportIssue,
    ImportJob,
    ImportRow,
    ImportValueMapping,
    MappingKind,
    MappingStatus,
)
from app.schemas.errors import ErrorResponse
from app.schemas.imports import (
    ApproveMappingIn,
    CommitIn,
    ImportJobOut,
    ImportJobSummary,
    ImportProfileOut,
    IssueOut,
    MappingDecisionIn,
    MappingIn,
    RowDecisionIn,
    RowOut,
    ValueMappingOut,
    VersionIn,
)
from app.schemas.pagination import Page
from app.services.identity.accounts import decode_cursor, encode_cursor
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.imports import jobs, reports, storage
from app.services.imports.profiles import PROFILES, ProfileSpec, get_profile

router = APIRouter(
    prefix="/imports",
    tags=["imports"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)

ViewImports = Annotated[AuthContext, Depends(require_permission(Permission.IMPORTS_VIEW))]
ManageMappings = Annotated[
    AuthContext,
    Depends(require_permission(Permission.IMPORTS_VIEW, Permission.IMPORTS_MAPPINGS_MANAGE)),
]
XLSX_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}
XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
# Domain permissions a profile's commit writes with (no privilege escalation via imports).
COMMIT_DOMAIN_PERMISSIONS = {
    "employees": (Permission.EMPLOYEES_MANAGE, Permission.REPORTING_LINES_MANAGE),
    "organisation": (Permission.ORGANISATION_MANAGE,),
}


def _require(auth: AuthContext, *codes: str) -> None:
    if not all(auth.has(code) for code in codes):
        raise AppError(403, "forbidden", "You do not have permission to perform this action.")


def _run_permission(profile: str) -> str:
    return f"imports.{profile}.run"


def _job(db: DbSessionDep, job_id: uuid.UUID, *, for_update: bool = False) -> ImportJob:
    return jobs.get_job(db, job_id, for_update=for_update)


def _attachment(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type=XLSX_MEDIA,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


# ------------------------------------------------------------------------------ profiles


@router.get("/profiles", response_model=list[ImportProfileOut], summary="Import profiles")
def list_profiles(auth: ViewImports) -> list[ImportProfileOut]:
    latest: dict[str, ProfileSpec] = {}
    for (code, version), profile in sorted(PROFILES.items()):
        if code not in latest or version > latest[code].version:
            latest[code] = profile
    return [profile_out(profile, auth.permissions) for profile in latest.values()]


@router.get("/profiles/{code}/template", summary="Download the standard template (.xlsx)")
def download_template(code: str, _auth: ViewImports) -> Response:
    profile = get_profile(code)
    if profile is None:
        raise AppError(404, "import_profile_not_found", "Import profile not found.")
    return _attachment(
        reports.template(profile), f"lms-import-{profile.code}-v{profile.version}-template.xlsx"
    )


# ---------------------------------------------------------------------------------- jobs


@router.post(
    "",
    response_model=ImportJobOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a workbook",
)
async def upload_workbook(
    request: Request,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
    profile: Annotated[str, Query(max_length=50)],
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.upload"):
        _require(auth, _run_permission(profile))
        content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
        if content_type not in XLSX_TYPES:
            raise AppError(415, "file_type_not_allowed", "Upload the workbook as an .xlsx file.")
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.import_max_upload_bytes:
                raise AppError(413, "file_too_large", "The file exceeds the upload size limit.")
            chunks.append(chunk)
        filename = unquote(request.headers.get("x-file-name", ""))[:300]
        job = jobs.upload(
            db,
            settings,
            actor=auth.actor,
            meta=meta,
            profile_code=profile,
            filename=filename,
            data=b"".join(chunks),
        )
        try:
            db.commit()
        except Exception:
            storage.remove(settings, job.public_id)  # the job was never recorded
            raise
    return job_out(db, job)


@router.get("", response_model=Page[ImportJobSummary], summary="Import jobs (newest first)")
def list_jobs(
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
    status_filter: Annotated[str | None, Query(alias="status", max_length=30)] = None,
    profile: Annotated[str | None, Query(max_length=50)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[ImportJobSummary]:
    jobs.reconcile_storage(db, settings, actor=auth.actor, meta=meta)
    query = select(ImportJob).order_by(ImportJob.id.desc()).limit(limit + 1)
    if status_filter:
        query = query.where(ImportJob.status == status_filter)
    if profile:
        query = query.where(ImportJob.profile_code == profile)
    if (before := decode_cursor(cursor)) is not None:
        query = query.where(ImportJob.id < before)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return Page[ImportJobSummary](items=job_summaries(db, rows[:limit]), next_cursor=next_cursor)


@router.get(
    "/mappings", response_model=Page[ValueMappingOut], summary="Reference mapping review queue"
)
def list_mappings(
    _auth: ViewImports,
    db: DbSessionDep,
    kind: Annotated[MappingKind | None, Query()] = None,
    status_filter: Annotated[MappingStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[ValueMappingOut]:
    query = select(ImportValueMapping).order_by(ImportValueMapping.id.desc()).limit(limit + 1)
    if kind is not None:
        query = query.where(ImportValueMapping.kind == kind)
    if status_filter is not None:
        query = query.where(ImportValueMapping.status == status_filter)
    if (before := decode_cursor(cursor)) is not None:
        query = query.where(ImportValueMapping.id < before)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return Page[ValueMappingOut](items=mappings_out(db, rows[:limit]), next_cursor=next_cursor)


def _finish_mapping(db: DbSessionDep, result: ImportValueMapping) -> ValueMappingOut:
    db.commit()
    return mappings_out(db, [result])[0]


@router.post(
    "/mappings/{mapping_id}/approve", response_model=ValueMappingOut, summary="Approve a mapping"
)
def approve_mapping(
    mapping_id: uuid.UUID,
    body: ApproveMappingIn,
    auth: ManageMappings,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ValueMappingOut:
    with audit_denials(db, auth, meta, "import.mapping.approve"):
        mapping = jobs.get_mapping(db, mapping_id)
        result = jobs.approve_mapping(
            db,
            mapping,
            actor=auth.actor,
            meta=meta,
            version=body.version,
            target_public_id=body.target_public_id,
            reason=body.reason,
        )
        return _finish_mapping(db, result)


@router.post(
    "/mappings/{mapping_id}/reject", response_model=ValueMappingOut, summary="Reject a mapping"
)
def reject_mapping(
    mapping_id: uuid.UUID,
    body: MappingDecisionIn,
    auth: ManageMappings,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ValueMappingOut:
    with audit_denials(db, auth, meta, "import.mapping.reject"):
        mapping = jobs.get_mapping(db, mapping_id)
        result = jobs.reject_mapping(
            db, mapping, actor=auth.actor, meta=meta, version=body.version, reason=body.reason
        )
        return _finish_mapping(db, result)


@router.post(
    "/mappings/{mapping_id}/withdraw",
    response_model=ValueMappingOut,
    summary="Withdraw a decided mapping (kept as history; the label returns to the queue)",
)
def withdraw_mapping(
    mapping_id: uuid.UUID,
    body: MappingDecisionIn,
    auth: ManageMappings,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ValueMappingOut:
    with audit_denials(db, auth, meta, "import.mapping.withdraw"):
        mapping = jobs.get_mapping(db, mapping_id)
        result = jobs.supersede_mapping(
            db, mapping, actor=auth.actor, meta=meta, version=body.version, reason=body.reason
        )
        return _finish_mapping(db, result)


@router.get("/{job_id}", response_model=ImportJobOut, summary="Import job")
def get_job(
    job_id: uuid.UUID,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    job = _job(db, job_id)
    if jobs.housekeep_job(db, settings, job, actor=auth.actor, meta=meta):
        db.commit()
        jobs.discard_released_file(settings, job)
    return job_out(db, job)


@router.put("/{job_id}/mapping", response_model=ImportJobOut, summary="Confirm the column mapping")
def set_mapping(
    job_id: uuid.UUID,
    body: MappingIn,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.mapping_set"):
        job = _job(db, job_id, for_update=True)
        _require(auth, _run_permission(job.profile_code))
        jobs.set_mapping(
            db,
            settings,
            job,
            actor=auth.actor,
            meta=meta,
            version=body.version,
            sections=[section.model_dump() for section in body.sections],
        )
        db.commit()
    return job_out(db, job)


@router.post(
    "/{job_id}/validate",
    response_model=ImportJobOut,
    summary="Validate (dry run; nothing is written)",
)
def validate_job(
    job_id: uuid.UUID,
    body: VersionIn,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.validate"):
        job = _job(db, job_id, for_update=True)
        _require(auth, _run_permission(job.profile_code))
        job = jobs.validate(db, settings, job, actor=auth.actor, meta=meta, version=body.version)
        db.commit()
    return job_out(db, job)


@router.post(
    "/{job_id}/rows/{row_id}/decision",
    response_model=ImportJobOut,
    summary="Skip a row or confirm a duplicate candidate",
)
def decide_row(
    job_id: uuid.UUID,
    row_id: int,
    body: RowDecisionIn,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.row_decision"):
        job = _job(db, job_id, for_update=True)
        _require(auth, _run_permission(job.profile_code))
        jobs.decide_row(
            db,
            settings,
            job,
            row_id,
            actor=auth.actor,
            meta=meta,
            version=body.version,
            decision=body.decision,
            reason=body.reason,
        )
        db.commit()
    return job_out(db, job)


@router.post(
    "/{job_id}/commit", response_model=ImportJobOut, summary="Approve and commit (one transaction)"
)
def commit_job(
    job_id: uuid.UUID,
    body: CommitIn,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.commit"):
        job = _job(db, job_id)
        _require(
            auth,
            f"imports.{job.profile_code}.commit",
            *COMMIT_DOMAIN_PERMISSIONS.get(job.profile_code, ()),
        )
        db.rollback()  # the commit takes its locks in a fresh transaction
        job = jobs.commit(
            db,
            settings,
            job_id,
            actor=auth.actor,
            meta=meta,
            version=body.version,
            apply_updates=body.apply_updates,
        )
        db.commit()
    jobs.discard_released_file(settings, job)
    return job_out(db, job)


@router.post("/{job_id}/cancel", response_model=ImportJobOut, summary="Cancel an open import")
def cancel_job(
    job_id: uuid.UUID,
    body: VersionIn,
    auth: ViewImports,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ImportJobOut:
    with audit_denials(db, auth, meta, "import.cancel"):
        job = _job(db, job_id, for_update=True)
        _require(auth, _run_permission(job.profile_code))
        jobs.cancel(db, job, actor=auth.actor, meta=meta, version=body.version)
        db.commit()
    jobs.discard_released_file(settings, job)
    return job_out(db, job)


@router.get("/{job_id}/rows", response_model=Page[RowOut], summary="Staged rows")
def list_rows(
    job_id: uuid.UUID,
    _auth: ViewImports,
    db: DbSessionDep,
    section: Annotated[str | None, Query(max_length=30)] = None,
    outcome: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[RowOut]:
    job = _job(db, job_id)
    query = (
        select(ImportRow).where(ImportRow.job_id == job.id).order_by(ImportRow.id).limit(limit + 1)
    )
    if section:
        query = query.where(ImportRow.section == section)
    if outcome:
        query = query.where(ImportRow.outcome == outcome)
    if (after := decode_cursor(cursor)) is not None:
        query = query.where(ImportRow.id > after)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return Page[RowOut](items=rows_out(db, rows[:limit]), next_cursor=next_cursor)


@router.get("/{job_id}/issues", response_model=Page[IssueOut], summary="Issues")
def list_issues(
    job_id: uuid.UUID,
    _auth: ViewImports,
    db: DbSessionDep,
    severity: Annotated[str | None, Query(max_length=10)] = None,
    code: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[IssueOut]:
    job = _job(db, job_id)
    query = (
        select(ImportIssue)
        .where(ImportIssue.job_id == job.id)
        .order_by(ImportIssue.id)
        .limit(limit + 1)
    )
    if severity:
        query = query.where(ImportIssue.severity == severity)
    if code:
        query = query.where(ImportIssue.code == code)
    if (after := decode_cursor(cursor)) is not None:
        query = query.where(ImportIssue.id > after)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return Page[IssueOut](
        items=[issue_out(issue) for issue in rows[:limit]], next_cursor=next_cursor
    )


@router.get("/{job_id}/error-report", summary="Download the issues as .xlsx (formula-safe)")
def error_report(job_id: uuid.UUID, _auth: ViewImports, db: DbSessionDep) -> Response:
    job = _job(db, job_id)
    issues = db.scalars(
        select(ImportIssue)
        .where(ImportIssue.job_id == job.id)
        .order_by(ImportIssue.sheet, ImportIssue.row_number, ImportIssue.id)
    )
    return _attachment(reports.error_report(issues), f"lms-import-{job.public_id}-issues.xlsx")
