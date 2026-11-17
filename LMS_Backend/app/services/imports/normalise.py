"""Deterministic cell normalisation for import profiles (no guessing).

Every function returns ``Normalised(value, issue)``: either a clean value or an issue
code (with parameters) that the validator records against the cell. Blank cells give
``value=None`` and no issue; whether a blank is allowed is decided by the caller.

Rules (Stage D, profile employees v1):

* **Employee codes** are text. A numeric cell is accepted only when its number
  format unambiguously fixes the width (``00000`` -> zero-padded to 5 digits);
  any other numeric code is flagged for manual review, because leading zeros may
  already have been lost. Text codes follow the server rule (trim, capitals).
* **Dates**: real Excel dates, ISO ``YYYY-MM-DD``, or day-first ``DD-MM-YYYY`` /
  ``DD/MM/YYYY`` / ``DD.MM.YYYY`` / ``DD-Mon-YYYY`` (profile date order DMY).
  Two-digit years, bare numbers and impossible dates are rejected - never guessed.
* **Status**: Active / On leave / Separated only; blank = not recorded (NULL).
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

from app.services.imports.profiles import normalise_label

_CODE = re.compile(r"^[A-Z0-9][A-Z0-9/._-]{0,29}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ZERO_FORMAT = re.compile(r"^0+$")
_MONTHS = {
    name: index
    for index, names in enumerate(
        (
            ("jan", "january"),
            ("feb", "february"),
            ("mar", "march"),
            ("apr", "april"),
            ("may",),
            ("jun", "june"),
            ("jul", "july"),
            ("aug", "august"),
            ("sep", "sept", "september"),
            ("oct", "october"),
            ("nov", "november"),
            ("dec", "december"),
        ),
        start=1,
    )
    for name in names
}
_STATUS = {
    "active": "active",
    "on leave": "on_leave",
    "on_leave": "on_leave",
    "separated": "separated",
}
_LANGUAGES = {
    "en": "en",
    "english": "en",
    "bn": "bn",
    "bengali": "bn",
    "bangla": "bn",
    "বাংলা": "bn",
    "hi": "hi",
    "hindi": "hi",
    "हिन्दी": "hi",
    "हिंदी": "hi",
    "gu": "gu",
    "gujarati": "gu",
    "ગુજરાતી": "gu",
}
_ASSIGNMENT_TYPES = {
    "primary": "primary",
    "additional": "additional",
    "acting": "acting",
    "deputation": "deputation",
}


@dataclass(frozen=True)
class Normalised:
    value: Any = None
    issue: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


BLANK = Normalised()


def source_text(value: Any) -> str | None:
    """The cell as text for display in issues (truncated; never a formula result)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        text = value.date().isoformat() if value.time() == time(0) else value.isoformat(sep=" ")
    elif isinstance(value, date):
        text = value.isoformat()
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)
    return text.strip()[:200] or None


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def employee_code(value: Any, number_format: str | None) -> Normalised:
    if _blank(value):
        return BLANK
    if isinstance(value, bool):
        return Normalised(issue="employee_code_invalid")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            return Normalised(issue="employee_code_invalid")
        number = int(value)
        fmt = (number_format or "").strip()
        if number >= 0 and _ZERO_FORMAT.fullmatch(fmt) and len(str(number)) <= len(fmt):
            return Normalised(str(number).zfill(len(fmt)))
        return Normalised(issue="employee_code_numeric", params={"value": str(number)})
    if not isinstance(value, str):
        return Normalised(issue="employee_code_invalid")
    code = value.strip().upper()
    if not _CODE.fullmatch(code):
        return Normalised(issue="employee_code_invalid")
    return Normalised(code)


def text(value: Any, max_length: int | None) -> Normalised:
    if _blank(value):
        return BLANK
    if isinstance(value, (datetime, date)):
        return Normalised(issue="text_expected")
    raw = value if isinstance(value, str) else (source_text(value) or "")
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if max_length is not None and len(cleaned) > max_length:
        return Normalised(issue="value_too_long", params={"max": max_length})
    return Normalised(cleaned)


def email(value: Any) -> Normalised:
    result = text(value, 254)
    if result.issue or result.value is None:
        return result
    if not _EMAIL.fullmatch(result.value):
        return Normalised(issue="email_invalid")
    return Normalised(result.value.lower())


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_date(value: Any) -> Normalised:
    if _blank(value):
        return BLANK
    if isinstance(value, datetime):
        if value.time() != time(0):
            return Normalised(issue="date_has_time")
        return Normalised(value.date())
    if isinstance(value, date):
        return Normalised(value)
    if isinstance(value, (int, float)):
        # A bare number in a cell not formatted as a date: possibly a serial date,
        # possibly not - never guessed.
        return Normalised(issue="date_numeric")
    if not isinstance(value, str):
        return Normalised(issue="date_invalid")
    raw = value.strip()
    if match := re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", raw):
        parsed = _safe_date(int(match[1]), int(match[2]), int(match[3]))
        return Normalised(parsed) if parsed else Normalised(issue="date_invalid")
    if match := re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", raw):
        if len(match[3]) != 4:
            return Normalised(issue="date_ambiguous")
        parsed = _safe_date(int(match[3]), int(match[2]), int(match[1]))
        return Normalised(parsed) if parsed else Normalised(issue="date_invalid")
    if match := re.fullmatch(r"(\d{1,2})[-/. ]([A-Za-z]{3,9})[-/., ]+(\d{2,4})", raw):
        month = _MONTHS.get(match[2].lower())
        if month is None:
            return Normalised(issue="date_invalid")
        if len(match[3]) != 4:
            return Normalised(issue="date_ambiguous")
        parsed = _safe_date(int(match[3]), month, int(match[1]))
        return Normalised(parsed) if parsed else Normalised(issue="date_invalid")
    return Normalised(issue="date_invalid")


def status(value: Any) -> Normalised:
    if _blank(value):
        return BLANK  # not recorded - never treated as active
    if not isinstance(value, str):
        return Normalised(issue="status_invalid")
    mapped = _STATUS.get(normalise_label(value)) or _STATUS.get(value.strip().lower())
    return Normalised(mapped) if mapped else Normalised(issue="status_invalid")


def language(value: Any) -> Normalised:
    if _blank(value):
        return BLANK
    if not isinstance(value, str):
        return Normalised(issue="language_invalid")
    mapped = _LANGUAGES.get(normalise_label(value)) or _LANGUAGES.get(value.strip())
    return Normalised(mapped) if mapped else Normalised(issue="language_invalid")


def assignment_type(value: Any) -> Normalised:
    if _blank(value):
        return Normalised("primary")  # documented profile default (template instructions)
    if not isinstance(value, str):
        return Normalised(issue="assignment_type_invalid")
    mapped = _ASSIGNMENT_TYPES.get(normalise_label(value))
    return Normalised(mapped) if mapped else Normalised(issue="assignment_type_invalid")


def reference_text(value: Any, max_length: int | None) -> Normalised:
    """A reference cell (unit, designation, ...) as cleaned text; resolution is separate."""
    if isinstance(value, (datetime, date)):
        return Normalised(issue="text_expected")
    return text(value, max_length)
