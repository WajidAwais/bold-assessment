"""Import use case: parse -> plan (validate, merge) -> batched persist -> report."""

import csv
import io
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import owner_connection
from app.domain.import_plan import (
    CSV_COLUMNS,
    ImportRow,
    Merge,
    Rejection,
    lookup_keys,
    parse_rows,
    plan_import,
)
from app.repositories import candidates as candidate_repo

MAX_IMPORT_BYTES = 5 * 1024 * 1024

# The csv module refuses fields over 128 KiB by default; a single field may
# legitimately use the whole size budget (e.g. a long note).
csv.field_size_limit(MAX_IMPORT_BYTES)


class InvalidImportFile(ValueError):
    """The file as a whole can't be imported; no row has been processed."""


class ImportFileTooLarge(InvalidImportFile):
    """The file is over ``MAX_IMPORT_BYTES``; no row has been processed."""


@dataclass(frozen=True)
class ImportReport:
    imported: int
    merged: int
    rejected: list[Rejection]
    merges: list[Merge]


def parse_csv(data: bytes) -> list[ImportRow]:
    """Decode and split the file into records, refusing a bad file as a whole."""
    if len(data) > MAX_IMPORT_BYTES:
        raise ImportFileTooLarge(f"file is larger than {MAX_IMPORT_BYTES} bytes")
    try:
        text = data.decode("utf-8-sig")  # tolerates an Excel byte-order mark
    except UnicodeDecodeError as exc:
        raise InvalidImportFile("file is not valid UTF-8") from exc

    reader = csv.DictReader(io.StringIO(text, newline=""))
    missing = [column for column in CSV_COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise InvalidImportFile(f"missing columns: {', '.join(missing)}")
    try:
        # enumerate counts CSV records, so a multi-line note doesn't shift row numbers.
        return [ImportRow(number, record) for number, record in enumerate(reader, start=1)]
    except csv.Error as exc:
        raise InvalidImportFile(f"file is not a readable CSV: {exc}") from exc


async def import_candidates(owner_engine: AsyncEngine, data: bytes) -> ImportReport:
    parsed = parse_rows(parse_csv(data))
    emails, legacy_ids = lookup_keys(parsed)

    # One transaction for the whole import: it succeeds or fails as a whole.
    async with owner_connection(owner_engine) as conn:
        existing = await candidate_repo.find_existing(conn, emails, legacy_ids)
        plan = plan_import(parsed, existing)
        await candidate_repo.insert_many(conn, plan.new_candidates)
        await candidate_repo.fill_blanks(conn, plan.blank_fills)

    return ImportReport(
        imported=len(plan.new_candidates),
        merged=len(plan.merges),
        rejected=plan.rejections,
        merges=plan.merges,
    )
