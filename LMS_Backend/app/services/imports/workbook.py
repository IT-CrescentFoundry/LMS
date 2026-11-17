"""Workbook safety checks, inspection and streaming row reading (Stage D).

Security (EXCEL_IMPORT_PROFILES §10):

* ``.xlsx`` only, recognised by content (ZIP container with an OOXML workbook part),
  never by extension alone; legacy ``.xls``, encrypted (OLE) and macro-enabled files
  are rejected;
* bounded upload size, ZIP entry count, total expanded size and per-entry
  compression ratio (zip-bomb protection); unsafe entry names are rejected;
* ``openpyxl`` in read-only, ``data_only`` mode with ``defusedxml`` (installed, so
  openpyxl uses it): formulas are never evaluated (cached results only), macros,
  links and embedded objects are never loaded;
* row/column/sheet limits (and a total-row limit per import, sized so validation
  and commit finish within the browser's request timeout) are enforced while
  streaming - a workbook is never fully materialised in memory;
* only *mapped* columns are ever taken from a row; openpyxl still parses the XML of
  the other cells in the row (and loads the shared-strings table) in memory, but
  those values are never copied, stored, logged or reported;
* malformed workbook XML anywhere (structure, sheet data, merged ranges) is reported
  as ``422 file_corrupted``, never as an unhandled server error.
"""

import io
import posixpath
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from defusedxml import ElementTree as SafeET
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

from app.core.errors import AppError
from app.services.imports.profiles import (
    ProfileSpec,
    is_excluded_header,
    normalise_label,
    suggest_field,
    suggest_section,
)

_NS_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_NS_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_NS_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


@dataclass(frozen=True)
class Limits:
    max_upload_bytes: int
    max_expanded_bytes: int
    max_zip_entries: int
    max_compression_ratio: int
    max_sheets: int
    max_rows: int
    max_columns: int
    max_total_rows: int = 6_000


def _reject(code: str, message: str) -> AppError:
    return AppError(422, code, message)


@contextmanager
def malformed_workbook_as_422() -> Iterator[None]:
    """Workbook reading only (no database work inside): any parser failure is a 422.

    openpyxl and the XML scans raise arbitrary exceptions (``ValueError``,
    ``KeyError``, ...) on malformed content; they must never surface as a 500.
    """
    try:
        yield
    except AppError:
        raise
    except Exception as exc:
        raise _reject("file_corrupted", "The workbook is damaged and cannot be read.") from exc


def check_file(data: bytes, filename: str, limits: Limits) -> zipfile.ZipFile:
    """Level-1 file validation. Returns the opened ZIP (caller closes) or raises 422."""
    if not filename.lower().endswith(".xlsx"):
        raise _reject("file_extension_not_allowed", "Only .xlsx workbooks can be imported.")
    if not data:
        raise _reject("file_empty", "The file is empty.")
    if len(data) > limits.max_upload_bytes:
        raise AppError(413, "file_too_large", "The file exceeds the upload size limit.")
    if data.startswith(_OLE_MAGIC):
        raise _reject(
            "file_encrypted_or_legacy",
            "Encrypted workbooks and legacy .xls files cannot be imported. Save as an "
            "unprotected .xlsx workbook.",
        )
    if not data.startswith(b"PK\x03\x04"):
        raise _reject("file_not_xlsx", "The file is not an .xlsx workbook.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise _reject("file_corrupted", "The workbook is damaged and cannot be read.") from exc
    infos = archive.infolist()
    try:
        if len(infos) > limits.max_zip_entries:
            raise _reject("file_too_complex", "The workbook contains too many parts.")
        expanded = 0
        for info in infos:
            name = info.filename
            if (
                name.startswith(("/", "\\"))
                or "\\" in name
                or ".." in posixpath.normpath(name).split("/")
            ):
                raise _reject("file_unsafe_entry", "The workbook contains an unsafe part name.")
            if info.flag_bits & 0x1:
                raise _reject("file_encrypted_or_legacy", "Encrypted workbooks cannot be imported.")
            expanded += info.file_size
            if expanded > limits.max_expanded_bytes:
                raise _reject(
                    "file_expansion_limit", "The workbook expands beyond the allowed size."
                )
            if (
                info.compress_size
                and info.file_size > 1_000_000
                and (info.file_size / info.compress_size > limits.max_compression_ratio)
            ):
                raise _reject("file_expansion_limit", "The workbook is compressed suspiciously.")
        names = {info.filename for info in infos}
        if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
            raise _reject("file_not_xlsx", "The file is not an .xlsx workbook.")
        content_types = archive.read("[Content_Types].xml")
        if b"macroEnabled" in content_types or any(
            n.lower().endswith("vbaproject.bin") for n in names
        ):
            raise _reject("file_macro_enabled", "Macro-enabled workbooks cannot be imported.")
        if b"spreadsheetml.sheet.main+xml" not in content_types:
            raise _reject("file_not_xlsx", "The file is not an .xlsx workbook.")
    except Exception:
        archive.close()
        raise
    return archive


def _sheet_parts(archive: zipfile.ZipFile) -> dict[str, str]:
    """Sheet name -> worksheet part path (from workbook.xml and its relationships)."""
    workbook = SafeET.fromstring(archive.read("xl/workbook.xml"))
    rels = SafeET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    targets = {
        rel.get("Id"): rel.get("Target", "") for rel in rels.iter(f"{_NS_PKG_REL}Relationship")
    }
    parts: dict[str, str] = {}
    for sheet in workbook.iter(f"{_NS_MAIN}sheet"):
        target = targets.get(sheet.get(f"{_NS_REL}id"), "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(f"xl/{target}")
        parts[sheet.get("name", "")] = path
    return parts


@dataclass
class SheetFlags:
    hidden_rows: set[int] = field(default_factory=set)
    merged_rows: set[int] = field(default_factory=set)


def sheet_flags(archive: zipfile.ZipFile, part: str) -> SheetFlags:
    """Hidden rows and rows touched by merged cells (bounded streaming XML scan)."""
    flags = SheetFlags()
    if part not in archive.namelist():
        return flags
    with archive.open(part) as stream:
        for _event, element in SafeET.iterparse(stream, events=("end",)):
            tag = element.tag
            if tag == f"{_NS_MAIN}row":
                if element.get("hidden") in ("1", "true") and (number := element.get("r")):
                    flags.hidden_rows.add(int(number))
                element.clear()
            elif tag == f"{_NS_MAIN}mergeCell" and (ref := element.get("ref")):
                _min_col, min_row, _max_col, max_row = range_boundaries(ref)
                if min_row is not None and max_row is not None and max_row - min_row <= 10_000:
                    flags.merged_rows.update(range(min_row, max_row + 1))
    return flags


def open_workbook(data: bytes) -> Any:
    try:
        return load_workbook(io.BytesIO(data), read_only=True, data_only=True, keep_links=False)
    except Exception as exc:
        raise _reject("file_corrupted", "The workbook is damaged and cannot be read.") from exc


def _cell_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def header_cells(worksheet: Any, row_number: int, limits: Limits) -> list[str]:
    for row in worksheet.iter_rows(min_row=row_number, max_row=row_number, values_only=True):
        values = list(row)
        if len(values) > limits.max_columns:
            values = values[: limits.max_columns + 1]
        return [_cell_text(value) for value in values]
    return []


def describe_headers(texts: list[str], section: Any) -> list[dict[str, Any]]:
    headers = []
    for index, header in enumerate(texts, start=1):
        if not header:
            continue
        excluded = is_excluded_header(header)
        headers.append(
            {
                "column": get_column_letter(index),
                "index": index,
                "text": header[:120],
                "excluded": excluded,
                "suggested_field": None
                if excluded or section is None
                else suggest_field(section, header),
            }
        )
    return headers


def inspect_workbook(
    data: bytes, filename: str, profile: ProfileSpec, limits: Limits
) -> list[dict[str, Any]]:
    """Sheets with their states, detected header row and header cells (texts only)."""
    archive = check_file(data, filename, limits)
    try:
        with malformed_workbook_as_422():
            parts = _sheet_parts(archive)
    finally:
        archive.close()
    workbook = open_workbook(data)
    try:
        with malformed_workbook_as_422():
            return _inspect_sheets(workbook, parts, profile, limits)
    finally:
        workbook.close()


def _inspect_sheets(
    workbook: Any, parts: dict[str, str], profile: ProfileSpec, limits: Limits
) -> list[dict[str, Any]]:
    sheets = workbook.worksheets
    if len(sheets) > limits.max_sheets:
        raise _reject("file_too_many_sheets", "The workbook has too many worksheets.")
    result = []
    for worksheet in sheets:
        suggested_kind = suggest_section(worksheet.title, profile)
        header_row, kind = _detect_header(worksheet, profile, suggested_kind, limits)
        section = profile.section(kind) if kind else None
        texts = header_cells(worksheet, header_row, limits) if header_row else []
        if len(texts) > limits.max_columns:
            raise _reject("sheet_too_many_columns", "A worksheet has too many columns.")
        result.append(
            {
                "name": worksheet.title[:100],
                "state": worksheet.sheet_state,
                "part": parts.get(worksheet.title),
                "dimensions": worksheet.calculate_dimension()
                if hasattr(worksheet, "calculate_dimension")
                else None,
                "suggested_section": kind,
                "header_row": header_row,
                "headers": describe_headers(texts, section),
            }
        )
    return result


def _detect_header(
    worksheet: Any, profile: ProfileSpec, preferred: str | None, limits: Limits
) -> tuple[int | None, str | None]:
    best: tuple[int, int, str] | None = None  # (matches, -row, kind)
    for row_number, row in enumerate(
        worksheet.iter_rows(min_row=1, max_row=profile.header_search_rows, values_only=True),
        start=1,
    ):
        texts = [_cell_text(value) for value in list(row)[: limits.max_columns]]
        for section in profile.sections:
            matches = len({suggest_field(section, text) for text in texts if text} - {None})
            if matches >= 2:
                score = (
                    matches + (1 if section.kind == preferred else 0),
                    -row_number,
                    section.kind,
                )
                if best is None or score > best:
                    best = score
    if best is None:
        return None, preferred
    return -best[1], best[2]


@dataclass(frozen=True)
class SourceRow:
    number: int
    cells: dict[str, tuple[Any, str | None]]  # field -> (value, number format)
    hidden: bool
    merged: bool


def iter_rows(
    worksheet: Any,
    header_row: int,
    columns: dict[int, str],
    header_texts: dict[int, str],
    flags: SheetFlags,
    limits: Limits,
) -> Iterator[SourceRow | str]:
    """Data rows below the header with only the mapped columns.

    Yields ``SourceRow`` items, or the marker strings ``"blank:<n>"`` and
    ``"repeated_header:<n>"`` for skipped rows. Raises 422 above the row limit.
    """
    seen = 0
    max_index = max(columns) if columns else 0
    for row_number, row in enumerate(
        worksheet.iter_rows(min_row=header_row + 1, max_col=max_index or None), start=header_row + 1
    ):
        seen += 1
        if seen > limits.max_rows:
            raise _reject("sheet_too_many_rows", "A worksheet has more rows than the import limit.")
        cells: dict[str, tuple[Any, str | None]] = {}
        for index, field_name in columns.items():
            cell = row[index - 1] if index - 1 < len(row) else None
            value = getattr(cell, "value", None)
            number_format = getattr(cell, "number_format", None)
            cells[field_name] = (value, number_format)
        values = [value for value, _ in cells.values()]
        if all(value is None or (isinstance(value, str) and not value.strip()) for value in values):
            yield f"blank:{row_number}"
            continue
        if all(
            normalise_label(_cell_text(cells[field][0]))
            == normalise_label(header_texts.get(index, ""))
            for index, field in columns.items()
        ):
            yield f"repeated_header:{row_number}"
            continue
        yield SourceRow(
            row_number, cells, row_number in flags.hidden_rows, row_number in flags.merged_rows
        )
