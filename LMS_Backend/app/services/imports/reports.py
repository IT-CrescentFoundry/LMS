"""Generated workbooks: profile templates and error reports (Stage D).

* The **template** has one worksheet per section with the canonical headers (the
  first alias of each field), employee-code columns pre-formatted as Text so leading
  zeros survive, and an *Instructions* sheet (fields, required, accepted values,
  date formats). It contains no data.
* The **error report** lists every issue (sheet, row, column, field, severity, code,
  source value, suggested correction). Cells that start with ``=``, ``+``, ``-``,
  ``@``, tab or carriage return are prefixed with an apostrophe so a spreadsheet
  never evaluates them (formula injection).
"""

import io
from collections.abc import Iterable
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from app.models.imports import ImportIssue
from app.services.imports.profiles import FieldType, ProfileSpec

_ACCEPTED = {
    FieldType.EMPLOYEE_CODE: "Text: letters, digits and / . _ - (max 30); leading zeros are kept",
    FieldType.DATE: "A real date, or YYYY-MM-DD, or DD-MM-YYYY / DD/MM/YYYY (day first)",
    FieldType.STATUS: "Active, On leave or Separated; leave blank if not recorded",
    FieldType.LANGUAGE: "en, bn, hi, gu (or English, Bengali, Hindi, Gujarati)",
    FieldType.ASSIGNMENT_TYPE: "Primary (default when blank), Additional, Acting or Deputation",
    FieldType.REFERENCE: "An existing code or exact name; other labels need an approved mapping",
    FieldType.EMAIL: "A work email address",
    FieldType.TEXT: "Text",
}
_SUGGESTIONS = {
    "required": "Fill in the value.",
    "employee_code_numeric": (
        "Format the column as Text and re-enter the codes with their leading zeros."
    ),
    "employee_code_invalid": "Use letters, digits and / . _ - only (max 30).",
    "date_numeric": "Enter a real date or DD-MM-YYYY.",
    "date_ambiguous": "Use a four-digit year.",
    "date_invalid": "Enter a valid date (DD-MM-YYYY or YYYY-MM-DD).",
    "status_invalid": "Use Active, On leave or Separated, or leave blank.",
    "reference_unmapped": "Use an existing code, or ask a reviewer to approve a mapping.",
    "reference_ambiguous": "Use the code: several records have this name.",
    "reference_rejected": "This label was rejected by a reviewer: correct it in the workbook.",
    "duplicate_in_file": "Keep one of the rows.",
    "employee_not_found": "Add the employee to the Employees section or correct the code.",
    "manager_not_found": "Correct the manager code or add the manager to the Employees section.",
}
_DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_DANGEROUS):
        return "'" + value
    return value


def _to_bytes(workbook: Workbook) -> bytes:
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def template(profile: ProfileSpec) -> bytes:
    workbook = Workbook()
    instructions = workbook.active
    instructions.title = "Instructions"
    instructions.append(["Section", "Column", "Required", "Accepted values"])
    for cell in instructions[1]:
        cell.font = Font(bold=True)
    for section in profile.sections:
        sheet = workbook.create_sheet(section.sheet_aliases[0])
        headers = [spec.aliases[0] if spec.aliases else spec.name for spec in section.fields]
        sheet.append(headers)
        for index, spec in enumerate(section.fields, start=1):
            sheet.cell(row=1, column=index).font = Font(bold=True)
            sheet.column_dimensions[get_column_letter(index)].width = max(
                14, len(headers[index - 1]) + 4
            )
            if spec.type == FieldType.EMPLOYEE_CODE:
                for row in range(2, 1002):
                    sheet.cell(row=row, column=index).number_format = "@"
            instructions.append(
                [
                    section.sheet_aliases[0],
                    headers[index - 1],
                    "Yes" if spec.required else "No",
                    _ACCEPTED[spec.type],
                ]
            )
    instructions.append([])
    instructions.append(
        [
            "Notes",
            "Do not add pay, bank, identity-number, birth date, gender, address, health, family "
            "or personal contact columns: they are never imported.",
        ]
    )
    instructions.append(
        [
            "",
            "Units, designations, locations, grades and levels are never created by an import: "
            "use existing records.",
        ]
    )
    instructions.append(["", "An end date is the LAST DAY on which the assignment applies."])
    for column, width in (("A", 18), ("B", 26), ("C", 10), ("D", 80)):
        instructions.column_dimensions[column].width = width
    return _to_bytes(workbook)


def error_report(issues: Iterable[ImportIssue]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Issues"
    sheet.append(
        [
            "Sheet",
            "Row",
            "Column",
            "Field",
            "Severity",
            "Code",
            "Source value",
            "Suggested correction",
        ]
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for issue in issues:
        sheet.append(
            [
                safe_cell(issue.sheet),
                issue.row_number,
                safe_cell(issue.column),
                safe_cell(issue.field),
                issue.severity,
                issue.code,
                safe_cell(issue.source_value),
                _SUGGESTIONS.get(issue.code, ""),
            ]
        )
    for column, width in zip("ABCDEFGH", (18, 8, 8, 18, 10, 28, 30, 60), strict=True):
        sheet.column_dimensions[column].width = width
    return _to_bytes(workbook)
