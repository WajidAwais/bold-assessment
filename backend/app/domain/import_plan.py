"""Deciding what an import does with each row. Pure Python, no I/O.

``plan_import`` turns raw CSV records into the Candidates to insert plus the
Import Report entries. Every row ends up in exactly one bucket: new Candidate,
Merge or Rejection. Nothing is dropped silently.

A row that fails the Candidate model is rejected with every reason, each using
a fixed prefix. A valid row is then placed by identity (ADR-0001):

- its email belongs to a Candidate already seen (in the database or earlier in
  the file): it Merges into that Candidate, whatever its Legacy ID, and only
  fills that Candidate's blank fields;
- otherwise, its Legacy ID belongs to another Candidate: ID Collision;
- otherwise it is a new Candidate.

The database counts as first-seen, so planning a file against the result of
importing it creates nothing and fills nothing.
"""

from collections.abc import Iterable, Mapping, Sequence
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


# The Candidate fields a Merge may fill. Required fields are never blank.
FILLABLE_FIELDS: tuple[str, ...] = tuple(
    name for name, info in Candidate.model_fields.items() if not info.is_required()
)


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
class BlankFill:
    """Values a Merge adds to the null fields of a stored Candidate."""

    email: str
    values: Mapping[str, Any]


@dataclass(frozen=True)
class ExistingCandidates:
    """The stored Candidates sharing an email or Legacy ID with the file,
    looked up in bulk before planning."""

    candidates: Sequence[Candidate] = ()


@dataclass
class ImportPlan:
    new_candidates: list[Candidate] = field(default_factory=list)
    blank_fills: list[BlankFill] = field(default_factory=list)
    merges: list[Merge] = field(default_factory=list)
    rejections: list[Rejection] = field(default_factory=list)


ID_COLLISION = "candidate_id collision"

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
    if error["type"] == "string_too_long":
        return f"{column} too long"
    return _INVALID_REASONS.get(field, f"invalid {column}")


def lookup_keys(rows: Iterable[ImportRow]) -> tuple[set[str], set[str]]:
    """The normalized emails and Legacy IDs to look up in the database."""
    parsed = [c for c in map(parse_candidate, rows) if isinstance(c, Candidate)]
    return {c.email for c in parsed}, {c.legacy_id for c in parsed}


def plan_import(rows: Iterable[ImportRow], existing: ExistingCandidates) -> ImportPlan:
    plan = ImportPlan()
    stored = {c.email: c for c in existing.candidates}
    # email -> the Candidate it identifies, with the blanks filled so far
    first_seen: dict[str, Candidate] = dict(stored)
    # Legacy ID -> email of the Candidate holding it
    legacy_id_owners = {c.legacy_id: c.email for c in existing.candidates}
    new_emails: list[str] = []

    for row in rows:
        parsed = parse_candidate(row)
        if isinstance(parsed, Rejection):
            plan.rejections.append(parsed)
            continue
        if (target := first_seen.get(parsed.email)) is not None:
            first_seen[parsed.email] = fill_blanks(target, parsed)
            plan.merges.append(Merge(row.row, row.candidate_id, target.legacy_id))
            continue
        if parsed.legacy_id in legacy_id_owners:
            plan.rejections.append(Rejection(row.row, row.candidate_id, ID_COLLISION))
            continue
        first_seen[parsed.email] = parsed
        legacy_id_owners[parsed.legacy_id] = parsed.email
        new_emails.append(parsed.email)

    plan.new_candidates = [first_seen[email] for email in new_emails]
    plan.blank_fills = [
        BlankFill(email, _filled_values(before, first_seen[email]))
        for email, before in stored.items()
        if first_seen[email] != before
    ]
    return plan


def fill_blanks(target: Candidate, other: Candidate) -> Candidate:
    """``target`` with its null fields taken from ``other``; nothing else changes."""
    fills = {
        name: getattr(other, name)
        for name in FILLABLE_FIELDS
        if getattr(target, name) is None and getattr(other, name) is not None
    }
    return target.model_copy(update=fills) if fills else target


def _filled_values(before: Candidate, after: Candidate) -> dict[str, Any]:
    return {
        name: getattr(after, name)
        for name in FILLABLE_FIELDS
        if getattr(before, name) != getattr(after, name)
    }
