"""Stage D import engine - unit tests (no database). Synthetic workbooks only."""

import io
import re
import zipfile
from datetime import date, datetime
from typing import Any

import pytest
from openpyxl import load_workbook

from app.core.errors import AppError
from app.models.imports import ImportStatus
from app.services.imports import normalise
from app.services.imports.employees_profile import parse
from app.services.imports.jobs import TRANSITIONS, can_transition, safe_filename, suggested_mapping
from app.services.imports.profiles import (
    EMPLOYEES_V1,
    get_profile,
    is_excluded_header,
    normalise_label,
    suggest_field,
    suggest_section,
)
from app.services.imports.reports import error_report, safe_cell, template
from app.services.imports.workbook import (
    Limits,
    _sheet_parts,
    check_file,
    inspect_workbook,
    open_workbook,
)
from tests.support.workbooks import build, rezip, standard

LIMITS = Limits(
    max_upload_bytes=2_000_000,
    max_expanded_bytes=20_000_000,
    max_zip_entries=200,
    max_compression_ratio=200,
    max_sheets=5,
    max_rows=50,
    max_columns=30,
    max_total_rows=40,
)


# --------------------------------------------------------------------------- normalisation


@pytest.mark.parametrize(
    ("value", "number_format", "expected"),
    [
        ("  e2e-0042 ", None, "E2E-0042"),
        ("00042", "@", "00042"),
        (42, "00000", "00042"),  # the format fixes the width unambiguously
        (12345, "00000", "12345"),
    ],
)
def test_employee_codes_keep_leading_zeros(
    value: object, number_format: str | None, expected: str
) -> None:
    assert normalise.employee_code(value, number_format).value == expected


@pytest.mark.parametrize(("value", "number_format"), [(42, "General"), (42, None), (42.0, "0")])
def test_numeric_codes_without_a_width_are_flagged_not_guessed(
    value: object, number_format: str | None
) -> None:
    result = normalise.employee_code(value, number_format)
    assert result.value is None and result.issue == "employee_code_numeric"


@pytest.mark.parametrize("value", ["A B", "-X1", "X" * 31, 4.5, True])
def test_invalid_codes(value: object) -> None:
    assert normalise.employee_code(value, None).issue == "employee_code_invalid"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (datetime(2025, 4, 1), date(2025, 4, 1)),
        (date(2025, 4, 1), date(2025, 4, 1)),
        ("2025-04-01", date(2025, 4, 1)),
        ("01-04-2025", date(2025, 4, 1)),  # day first (profile date order DMY)
        ("1/4/2025", date(2025, 4, 1)),
        ("01.04.2025", date(2025, 4, 1)),
        ("1-Apr-2025", date(2025, 4, 1)),
        ("29-02-2028", date(2028, 2, 29)),
    ],
)
def test_dates(value: object, expected: date) -> None:
    assert normalise.parse_date(value).value == expected


@pytest.mark.parametrize(
    ("value", "issue"),
    [
        ("01-04-25", "date_ambiguous"),
        (45000, "date_numeric"),
        ("31-02-2025", "date_invalid"),
        ("next week", "date_invalid"),
        (datetime(2025, 4, 1, 9, 30), "date_has_time"),
    ],
)
def test_dates_are_never_guessed(value: object, issue: str) -> None:
    result = normalise.parse_date(value)
    assert result.value is None and result.issue == issue


def test_missing_status_stays_not_recorded_and_unknown_values_are_errors() -> None:
    assert normalise.status(None).value is None and normalise.status(None).issue is None
    assert normalise.status("  ").value is None
    assert normalise.status("On Leave").value == "on_leave"
    assert normalise.status("Active").value == "active"
    for value in ("Left", "Resigned", "Y", 1):
        assert normalise.status(value).issue == "status_invalid"


def test_languages_assignment_types_and_emails() -> None:
    assert normalise.language("Hindi").value == "hi"
    assert normalise.language("ગુજરાતી").value == "gu"
    assert normalise.language("French").issue == "language_invalid"
    assert normalise.assignment_type(None).value == "primary"
    assert normalise.assignment_type("Deputation").value == "deputation"
    assert normalise.assignment_type("temporary").issue == "assignment_type_invalid"
    assert normalise.email("Person.One@Example.TEST").value == "person.one@example.test"
    assert normalise.email("not-an-email").issue == "email_invalid"
    assert normalise.text("x" * 201, 200).issue == "value_too_long"


# ------------------------------------------------------------------------------- profiles


@pytest.mark.parametrize(
    "header",
    [
        "CTC",
        "Monthly Salary",
        "Gross Pay",
        "Bank Account No.",
        "IFSC",
        "PAN",
        "Aadhaar No",
        "Date of Birth",
        "DOB",
        "Gender",
        "Home Address",
        "Mobile No",
        "Personal Email",
        "Blood Group",
        "Father's Name",
        "UAN",
        "PF No",
        "Basic",
        "HRA",
    ],
)
def test_sensitive_headers_are_excluded(header: str) -> None:
    assert is_excluded_header(header)


@pytest.mark.parametrize(
    "header", ["Employee Code", "Full Name", "Official Email Address", "Designation", "Department"]
)
def test_ordinary_headers_are_not_excluded(header: str) -> None:
    assert not is_excluded_header(header)


def test_header_aliases_are_exact_after_normalisation_only() -> None:
    section = EMPLOYEES_V1.section("employees")
    assert suggest_field(section, "  EMP. CODE ") == "employee_code"
    assert suggest_field(section, "Date of Joining") == "date_of_joining"
    assert suggest_field(section, "Employe Code") is None  # no fuzzy header matching
    assert suggest_field(section, "CTC") is None
    assert suggest_section("Employee Master", EMPLOYEES_V1) == "employees"
    assert suggest_section("Sheet1", EMPLOYEES_V1) is None
    assert normalise_label("Sales & BD") == "sales and bd"


def test_profile_versions_are_explicit() -> None:
    profile = get_profile("employees")
    assert profile is not None and (profile.code, profile.version) == ("employees", 1)
    assert get_profile("employees", 99) is None
    assert get_profile("skills") is None  # profiles 2-6 belong to later stages


# --------------------------------------------------------------------------- state machine


def test_state_machine_rejects_illegal_transitions() -> None:
    assert can_transition(ImportStatus.READY_FOR_APPROVAL, ImportStatus.COMMITTING)
    assert not can_transition(ImportStatus.MAPPING_REQUIRED, ImportStatus.COMMITTING)
    assert not can_transition(ImportStatus.VALIDATION_FAILED, ImportStatus.COMMITTING)
    assert not can_transition(ImportStatus.COMMITTING, ImportStatus.CANCELLED)
    for terminal in (
        ImportStatus.COMPLETED,
        ImportStatus.COMPLETED_WITH_SKIPS,
        ImportStatus.FAILED,
        ImportStatus.CANCELLED,
        ImportStatus.EXPIRED,
    ):
        assert terminal not in TRANSITIONS, terminal
        assert not can_transition(terminal, ImportStatus.VALIDATING)
    assert {target for targets in TRANSITIONS.values() for target in targets} <= set(ImportStatus)


def test_filenames_are_display_only_and_sanitised() -> None:
    assert safe_filename("..\\..\\etc/passwd.xlsx") == "passwd.xlsx"
    assert safe_filename("a\x00b\x1f.xlsx") == "ab.xlsx"
    assert safe_filename("") == "upload.xlsx"


# ---------------------------------------------------------------------- file security


def _check(data: bytes, name: str = "people.xlsx") -> str:
    with pytest.raises(AppError) as error:
        check_file(data, name, LIMITS).close()
    return error.value.code


def test_valid_workbook_passes_level_1() -> None:
    check_file(
        standard([["E-1", "Test Person", "Active", "2025-01-01", None]]), "ok.xlsx", LIMITS
    ).close()


def test_hostile_and_malformed_files_are_rejected() -> None:
    good = standard()
    assert _check(good, "people.xlsm") == "file_extension_not_allowed"
    assert _check(good, "people.csv") == "file_extension_not_allowed"
    assert _check(b"") == "file_empty"
    assert _check(b"x" * 2_000_001) == "file_too_large"
    assert _check(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 100) == "file_encrypted_or_legacy"
    assert _check(b"just some text, not a workbook") == "file_not_xlsx"
    assert _check(b"PK\x03\x04garbage") == "file_corrupted"
    assert _check(rezip(good, drop=["xl/workbook.xml"])) == "file_not_xlsx"
    assert _check(rezip(good, add={"xl/vbaProject.bin": b"macro"})) == "file_macro_enabled"
    assert _check(rezip(good, add={"../evil.txt": b"x"})) == "file_unsafe_entry"


def test_zip_bomb_and_entry_limits() -> None:
    bomb = rezip(standard(), add={"xl/media/blob.bin": b"\0" * 5_000_000})
    assert _check(bomb) == "file_expansion_limit"
    many = rezip(standard(), add={f"xl/media/f{i}.bin": b"x" for i in range(250)})
    assert _check(many) == "file_too_complex"


def test_inspection_detects_sections_headers_exclusions_and_states() -> None:
    data = build(
        {
            "Employee Master": [
                ["Synthetic export - do not use"],
                ["Emp Code", "Employee Name", "CTC", "Date of Birth", "Department", "Designation"],
                ["E-1", "Test Person", 100, "2000-01-01", "Operation", "Test Operator"],
            ],
            "Hidden": [["Employee Code", "Full Name"]],
        },
        hidden_sheets=["Hidden"],
    )
    sheets = inspect_workbook(data, "export.xlsx", EMPLOYEES_V1, LIMITS)
    master = sheets[0]
    assert master["header_row"] == 2 and master["suggested_section"] == "employees"
    by_text = {h["text"]: h for h in master["headers"]}
    assert by_text["CTC"]["excluded"] and by_text["Date of Birth"]["excluded"]
    assert by_text["Emp Code"]["suggested_field"] == "employee_code"
    assert by_text["CTC"]["suggested_field"] is None
    assert sheets[1]["state"] == "hidden"
    # Inspection records header texts only, never data cells.
    assert "100" not in repr(sheets) and "2000-01-01" not in repr(sheets)
    mapping = suggested_mapping(sheets)
    assert [(m["sheet"], m["section"]) for m in mapping] == [
        ("Employee Master", "employees")
    ]  # hidden sheet not suggested


def _sheet_xml(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read("xl/worksheets/sheet1.xml").decode()


@pytest.mark.parametrize(
    "damage",
    [
        lambda xml: re.sub(r'<row r="2"', '<row r="x2"', xml),  # row number not a number
        lambda xml: xml.replace('r="A2"', 'r="!!"'),  # impossible cell reference
        lambda xml: xml.replace(  # impossible merged range
            "</sheetData>", '</sheetData><mergeCells><mergeCell ref="ZZZZZ"/></mergeCells>'
        ),
    ],
)
def test_malformed_sheet_xml_is_a_file_error_never_a_crash(damage: Any) -> None:
    good = standard([["E-1", "Test Person", "Active", "2025-01-01", None]])
    bad = rezip(good, replace={"xl/worksheets/sheet1.xml": damage(_sheet_xml(good)).encode()})
    with pytest.raises(AppError) as error:
        inspect_workbook(bad, "bad.xlsx", EMPLOYEES_V1, LIMITS)
    assert (error.value.status_code, error.value.code) == (422, "file_corrupted")


def _parse(data: bytes, limits: Limits = LIMITS) -> Any:
    sheets = inspect_workbook(data, "x.xlsx", EMPLOYEES_V1, limits)
    mapping = suggested_mapping(sheets)
    for section in mapping:
        section["letters"] = {index: "?" for index in section["columns"]}
    archive = check_file(data, "x.xlsx", limits)
    workbook = open_workbook(data)
    try:
        return parse(workbook, archive, _sheet_parts(archive), mapping, EMPLOYEES_V1, limits)
    finally:
        workbook.close()
        archive.close()


def test_rows_per_import_are_capped_across_sections() -> None:
    rows = [[f"E-{n}", "Test Person", None, None, None] for n in range(30)]
    reporting = [[f"E-{n}", "E-0", "2025-01-01"] for n in range(1, 15)]
    assert len(_parse(standard(rows)).rows) == 30
    with pytest.raises(AppError) as error:
        _parse(standard(rows, reporting=reporting))  # 44 rows > 40
    assert (error.value.status_code, error.value.code) == (422, "import_too_many_rows")


def test_formulas_are_never_evaluated_and_formula_text_is_never_taken_as_data() -> None:
    data = build(
        {
            "Employees": [
                ["Employee Code", "Full Name"],
                ['=CONCATENATE("E-","77")', "Test Formula"],  # formula without a cached result
            ]
        }
    )
    [row] = _parse(data).rows
    assert "employee_code" not in row.values  # read as empty: nothing was calculated
    assert [issue.code for issue in row.issues] == ["required"]
    assert "CONCATENATE" not in repr(row.source)


def test_too_many_sheets_is_a_file_error() -> None:
    data = build({f"S{i}": [["a"]] for i in range(6)})
    with pytest.raises(AppError) as error:
        inspect_workbook(data, "many.xlsx", EMPLOYEES_V1, LIMITS)
    assert error.value.code == "file_too_many_sheets"


# -------------------------------------------------------------------------------- reports


def test_template_has_every_section_and_text_formatted_codes() -> None:
    workbook = load_workbook(io.BytesIO(template(EMPLOYEES_V1)))
    assert workbook.sheetnames == ["Instructions", "Employees", "Assignments", "Reporting"]
    assert workbook["Employees"]["A1"].value == "Employee Code"
    assert workbook["Employees"]["A2"].number_format == "@"
    assert workbook["Reporting"]["B2"].number_format == "@"


def test_error_report_neutralises_formula_injection() -> None:
    assert safe_cell('=HYPERLINK("x")') == '\'=HYPERLINK("x")'
    assert safe_cell("+1") == "'+1" and safe_cell("@x") == "'@x" and safe_cell("ok") == "ok"

    class Issue:
        sheet, row_number, column, field = "Employees", 2, "A", "employee_code"
        severity, code, source_value = "error", "required", "=cmd|' /c calc'!A0"

    workbook = load_workbook(io.BytesIO(error_report([Issue()])))  # type: ignore[list-item]
    cell = workbook["Issues"]["G2"]
    assert cell.data_type == "s" and str(cell.value).startswith("'=")
    with zipfile.ZipFile(io.BytesIO(error_report([]))) as archive:
        assert all(
            "<f>" not in archive.read(name).decode("utf-8", "ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )
