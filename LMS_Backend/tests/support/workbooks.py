"""Synthetic .xlsx workbooks for import tests (Stage D). Never real employee data."""

import io
import zipfile
from collections.abc import Sequence
from typing import Any

from openpyxl import Workbook

Cell = Any


def build(
    sheets: dict[str, Sequence[Sequence[Cell]]],
    *,
    formats: dict[tuple[str, int, int], str] | None = None,
    hidden_rows: dict[str, Sequence[int]] | None = None,
    merged: dict[str, Sequence[str]] | None = None,
    hidden_sheets: Sequence[str] = (),
) -> bytes:
    """Rows are lists of cell values (row 1 first). ``formats`` maps (sheet, row, col)."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(list(row))
        for (sheet_name, row_number, column), number_format in (formats or {}).items():
            if sheet_name == name:
                sheet.cell(row=row_number, column=column).number_format = number_format
        for row_number in (hidden_rows or {}).get(name, ()):
            sheet.row_dimensions[row_number].hidden = True
        for ref in (merged or {}).get(name, ()):
            sheet.merge_cells(ref)
        if name in hidden_sheets:
            sheet.sheet_state = "hidden"
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


EMPLOYEE_HEADERS = [
    "Employee Code",
    "Full Name",
    "Employment Status",
    "Date of Joining",
    "Work Email",
]
ASSIGNMENT_HEADERS = [
    "Employee Code",
    "Assignment Type",
    "Organisation Unit",
    "Designation",
    "Effective From",
]
REPORTING_HEADERS = ["Employee Code", "Manager Code", "Effective From"]


def standard(
    employees: Sequence[Sequence[Cell]] = (),
    assignments: Sequence[Sequence[Cell]] = (),
    reporting: Sequence[Sequence[Cell]] = (),
    **kwargs: Any,
) -> bytes:
    sheets: dict[str, Sequence[Sequence[Cell]]] = {"Employees": [EMPLOYEE_HEADERS, *employees]}
    if assignments:
        sheets["Assignments"] = [ASSIGNMENT_HEADERS, *assignments]
    if reporting:
        sheets["Reporting"] = [REPORTING_HEADERS, *reporting]
    return build(sheets, **kwargs)


def rezip(
    data: bytes,
    *,
    add: dict[str, bytes] | None = None,
    drop: Sequence[str] = (),
    replace: dict[str, bytes] | None = None,
) -> bytes:
    """Rewrite the ZIP container (for hostile-file tests)."""
    source = zipfile.ZipFile(io.BytesIO(data))
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target:
        for info in source.infolist():
            if info.filename in drop:
                continue
            payload = (replace or {}).get(info.filename, source.read(info.filename))
            target.writestr(info.filename, payload)
        for name, payload in (add or {}).items():
            target.writestr(name, payload)
    return buffer.getvalue()
