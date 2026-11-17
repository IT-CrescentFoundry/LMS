"""Protected storage for uploaded workbooks (Stage D).

* Files are named only by the import job's public UUID (``<uuid>.xlsx``): no part of
  a user-supplied filename ever reaches the file system, so path traversal is not
  possible.
* The directory must be outside the source tree and is never served by the web
  application. Default: ``%LOCALAPPDATA%/CrescentLMS/imports`` on Windows,
  ``~/.local/share/crescent-lms/imports`` elsewhere (per-user, not synchronised).
* A file is kept only while its job is open. The database is the source of truth:
  a job that completes, fails, is cancelled or expires is first marked
  ``file_stored = false`` **in the same transaction as its new status**, and the file
  is deleted only after that transaction has committed (``remove``). A deletion that
  fails, or a crash between the commit and the deletion, leaves an orphan file that
  ``app.services.imports.jobs.reconcile_storage`` removes later; it never leaves an
  open job without its file.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.core.errors import AppError

_SOURCE_ROOT = Path(__file__).resolve().parents[4]  # repository root (LMS/)
_log = logging.getLogger(__name__)


def storage_dir(settings: Settings) -> Path:
    if settings.import_storage_dir is not None:
        base = settings.import_storage_dir
    elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "CrescentLMS" / "imports"
    else:
        base = Path.home() / ".local" / "share" / "crescent-lms" / "imports"
    resolved = base.resolve()
    if resolved == _SOURCE_ROOT or _SOURCE_ROOT in resolved.parents:
        raise AppError(
            500, "import_storage_misconfigured", "Import storage must be outside the source tree."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _path(settings: Settings, job_id: uuid.UUID) -> Path:
    return storage_dir(settings) / f"{uuid.UUID(str(job_id))}.xlsx"


def save(settings: Settings, job_id: uuid.UUID, data: bytes) -> None:
    path = _path(settings, job_id)
    temporary = path.with_suffix(".part")
    try:
        temporary.write_bytes(data)
        temporary.replace(path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        _log.warning("Import file could not be stored", extra={"job": str(job_id)})
        raise AppError(
            503,
            "import_storage_unavailable",
            "The uploaded file could not be stored. Try again later.",
        ) from exc


def load(settings: Settings, job_id: uuid.UUID) -> bytes:
    path = _path(settings, job_id)
    if not path.is_file():
        raise AppError(409, "import_file_unavailable", "The uploaded file is no longer available.")
    return path.read_bytes()


def exists(settings: Settings, job_id: uuid.UUID) -> bool:
    return _path(settings, job_id).is_file()


def remove(settings: Settings, job_id: uuid.UUID) -> bool:
    """Best-effort deletion; never raises. ``False`` leaves the file for reconciliation."""
    try:
        _path(settings, job_id).unlink(missing_ok=True)
    except OSError:
        _log.warning("Import file could not be deleted yet", extra={"job": str(job_id)})
        return False
    return True


@dataclass(frozen=True)
class StoredFile:
    path: Path
    job_id: uuid.UUID | None  # None: not a name this module creates
    partial: bool
    age_seconds: float


def stored_files(settings: Settings) -> list[StoredFile]:
    """Every file in the storage directory (for reconciliation)."""
    now = time.time()
    files = []
    for path in storage_dir(settings).iterdir():
        if not path.is_file():
            continue
        try:
            job_id: uuid.UUID | None = uuid.UUID(path.stem)
        except ValueError:
            job_id = None
        try:
            age = now - path.stat().st_mtime
        except OSError:
            continue
        files.append(StoredFile(path, job_id, path.suffix == ".part", age))
    return files


def discard(stored: StoredFile) -> bool:
    try:
        stored.path.unlink(missing_ok=True)
    except OSError:
        _log.warning("Orphan import file could not be deleted", extra={"file": stored.path.name})
        return False
    return True
