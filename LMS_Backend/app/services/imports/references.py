"""Reference resolution for import cells (units, designations, locations, grades, levels).

A source label resolves to an existing canonical record only by, in this order:

1. its **code** (case-insensitive, exact);
2. its **name / title** (normalised, exact) - when exactly one record has that name;
3. an **approved** ``import_value_mapping`` decision for the normalised label.

Anything else is *unresolved*: the label is staged as a ``pending`` mapping in the
review queue (never as a new canonical record), the row is blocked, and up to three
**suggestions** are offered with a score and reason. Suggestions are never applied
automatically; an authorised reviewer approves a mapping to an existing record (or
rejects it). A ``rejected`` label stays blocked until the workbook is corrected.
"""

import difflib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.imports import ImportValueMapping, MappingKind, MappingStatus
from app.models.occupation import Designation, Grade, JobLevel
from app.models.organisation import Location, OrgUnit
from app.services.imports.profiles import normalise_label

# Abbreviations expanded only to *rank suggestions*; never to resolve a label.
_ABBREVIATIONS = {
    "sr": "senior",
    "jr": "junior",
    "asst": "assistant",
    "asstt": "assistant",
    "dy": "deputy",
    "mgr": "manager",
    "engr": "engineer",
    "engg": "engineering",
    "exe": "executive",
    "exec": "executive",
    "dept": "department",
    "hod": "head of department",
    "opr": "operator",
    "tech": "technician",
    "supvr": "supervisor",
    "admin": "administration",
    "acct": "accounts",
    "accts": "accounts",
    "mfg": "manufacturing",
    "qa": "quality assurance",
    "qc": "quality control",
}

MODELS: dict[str, Any] = {
    MappingKind.ORG_UNIT: OrgUnit,
    MappingKind.DESIGNATION: Designation,
    MappingKind.LOCATION: Location,
    MappingKind.GRADE: Grade,
    MappingKind.JOB_LEVEL: JobLevel,
}


def label_of(kind: str, record: Any) -> str:
    return str(record.title if kind == MappingKind.DESIGNATION else record.name)


def _expanded(text: str) -> str:
    return " ".join(_ABBREVIATIONS.get(token, token) for token in normalise_label(text).split())


@dataclass(frozen=True)
class Candidate:
    public_id: uuid.UUID
    code: str
    label: str


@dataclass(frozen=True)
class Suggestion:
    public_id: str
    code: str
    label: str
    score: int
    reason: str


@dataclass(frozen=True)
class Resolution:
    public_id: uuid.UUID | None
    method: str | None  # code | name | mapping
    issue: str | None  # reference_unmapped | reference_ambiguous | reference_rejected
    suggestions: tuple[Suggestion, ...] = ()


@dataclass
class ReferenceIndex:
    """Canonical records and current mapping decisions, loaded once per validation."""

    by_code: dict[str, dict[str, Candidate]] = field(default_factory=dict)
    by_name: dict[str, dict[str, list[Candidate]]] = field(default_factory=dict)
    candidates: dict[str, list[Candidate]] = field(default_factory=dict)
    mappings: dict[tuple[str, str], ImportValueMapping] = field(default_factory=dict)
    unresolved: dict[tuple[str, str], str] = field(default_factory=dict)  # -> first source text

    @classmethod
    def load(cls, db: Session) -> "ReferenceIndex":
        index = cls()
        for kind, model in MODELS.items():
            codes: dict[str, Candidate] = {}
            names: dict[str, list[Candidate]] = defaultdict(list)
            items: list[Candidate] = []
            for record in db.scalars(select(model)):
                candidate = Candidate(record.public_id, record.code, label_of(kind, record))
                codes[record.code.casefold()] = candidate
                names[normalise_label(candidate.label)].append(candidate)
                items.append(candidate)
            index.by_code[kind], index.by_name[kind], index.candidates[kind] = (
                codes,
                dict(names),
                items,
            )
        for mapping in db.scalars(
            select(ImportValueMapping).where(ImportValueMapping.status != MappingStatus.SUPERSEDED)
        ):
            index.mappings[(mapping.kind, mapping.normalised_text)] = mapping
        return index

    def resolve(self, kind: str, text: str) -> Resolution:
        code_match = self.by_code[kind].get(text.strip().casefold())
        if code_match is not None:
            return Resolution(code_match.public_id, "code", None)
        normalised = normalise_label(text)
        named = self.by_name[kind].get(normalised, [])
        if len(named) == 1:
            return Resolution(named[0].public_id, "name", None)
        decision = self.mappings.get((kind, normalised))
        if decision is not None and decision.status == MappingStatus.APPROVED:
            return Resolution(decision.target_public_id, "mapping", None)
        if decision is not None and decision.status == MappingStatus.REJECTED:
            return Resolution(None, None, "reference_rejected")
        self.unresolved.setdefault((kind, normalised), text.strip()[:200])
        issue = "reference_ambiguous" if len(named) > 1 else "reference_unmapped"
        pool = named if named else self.candidates[kind]
        return Resolution(None, None, issue, tuple(self.suggest(kind, text, pool)))

    def suggest(
        self, kind: str, text: str, pool: list[Candidate] | None = None
    ) -> list[Suggestion]:
        target = _expanded(text)
        scored = []
        for candidate in pool if pool is not None else self.candidates[kind]:
            label = _expanded(candidate.label)
            ratio = difflib.SequenceMatcher(None, target, label).ratio()
            tokens_a, tokens_b = set(target.split()), set(label.split())
            overlap = len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)
            score = round(max(ratio, overlap) * 100)
            if score >= 60:
                reason = (
                    "same_words"
                    if tokens_a == tokens_b
                    else "similar_spelling"
                    if ratio >= overlap
                    else "shared_words"
                )
                scored.append(
                    Suggestion(
                        str(candidate.public_id), candidate.code, candidate.label, score, reason
                    )
                )
        scored.sort(key=lambda s: (-s.score, s.code))
        return scored[:3]
