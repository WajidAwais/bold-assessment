"""Deciding what an import does with each row. Pure Python, no I/O.

``plan_import`` turns raw CSV records into the Candidates to insert plus the
Import Report entries. Every row ends up in exactly one bucket: new Candidate,
Merge or Rejection. Nothing is dropped silently.

A row that fails the Candidate model is rejected with every reason, each using
a fixed prefix. Until ticket 04 brings first-seen Merge and ID Collision
detection, a row whose email or Legacy ID is already taken is rejected as a
duplicate.
"""

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.domain.candidate import Candidate

# CSV column -> Candidate field
CSV_COLUMNS: Mapping[str, str] = {
    "candidate_id": "legacy_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "region_code": "region",
    "desired_role": "desired_role",
    "salary_expectation": "salary",
    "applied_date": "applied_date",
    "status": "status",
    "source": "source",
    "notes": "notes",
}


@dataclass(frozen=True)
class ImportRow:
    """One CSV record. ``row`` is 1-based and excludes the header."""

    row: int
    values: Mapping[str, str | None]

    @property
    def candidate_id(self) -> str | None:
        value = (self.values.get("candidate_id") or "").strip()
        return value or None


@dataclass(frozen=True)
class Rejection:
    row: int
    candidate_id: str | None
    reason: str


@dataclass(frozen=True)
class Merge:
    row: int
    candidate_id: str | None
    merged_into: str


@dataclass(frozen=True)
class ExistingCandidates:
    """What the database already holds, looked up in bulk before planning."""

    emails: Set[str] = frozenset()
    legacy_ids: Set[str] = frozenset()


@dataclass
class ImportPlan:
    new_candidates: list[Candidate] = field(default_factory=list)
    merges: list[Merge] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)


# Candidate field -> CSV column, so reasons name the column the Admin must fix.
_COLUMN_FOR_FIELD: Mapping[str, str] = {field: column for column, field in CSV_COLUMNS.items()}

# The fixed reason for a present-but-unusable value, per Candidate field.
_INVALID_REASONS: Mapping[str, str] = {
    "email": "invalid email",
    "region": "unknown region",
    "status": "unknown status",
    "applied_date": "invalid date",
}


def parse_candidate(row: ImportRow) -> Candidate | Rejection:
    """Normalize one record into a Candidate, or reject it with every reason."""
    data = {model_field: row.values.get(column) for column, model_field in CSV_COLUMNS.items()}
    try:
        return Candidate.model_validate(data)
    except ValidationError as exc:
        reasons = [_reason(error) for error in exc.errors()]
        # One reason per field, in CSV column order (Pydantic reports in field order).
        return Rejection(row.row, row.candidate_id, "; ".join(dict.fromkeys(reasons)))


def _reason(error: Mapping[str, Any]) -> str:
    field = str(error["loc"][0])
    column = _COLUMN_FOR_FIELD[field]
    if error["input"] is None:  # blanks were nulled before validation
        return f"missing {column}"
    if error["type"] == "invalid_characters":
        return f"invalid characters in {column}"
    return _INVALID_REASONS.get(field, f"invalid {column}")


def lookup_keys(rows: Iterable[ImportRow]) -> tuple[set[str], set[str]]:
    """The normalized emails and Legacy IDs to look up in the database."""
    parsed = [c for c in map(parse_candidate, rows) if isinstance(c, Candidate)]
    return {c.email for c in parsed}, {c.legacy_id for c in parsed}


def plan_import(rows: Iterable[ImportRow], existing: ExistingCandidates) -> ImportPlan:
    plan = ImportPlan()
    seen_emails = set(existing.emails)
    seen_legacy_ids = set(existing.legacy_ids)

    for row in rows:
        parsed = parse_candidate(row)
        if isinstance(parsed, Rejection):
            plan.rejections.append(parsed)
            continue
        if parsed.email in seen_emails or parsed.legacy_id in seen_legacy_ids:
            plan.rejections.append(Rejection(row.row, row.candidate_id, "duplicate candidate"))
            continue
        seen_emails.add(parsed.email)
        seen_legacy_ids.add(parsed.legacy_id)
        plan.new_candidates.append(parsed)

    return plan
