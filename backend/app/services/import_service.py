"""Import use case: parse -> plan (validate, dedupe) -> batched persist -> report."""

import csv
import io
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import owner_connection
from app.domain.import_plan import ImportRow, Merge, Rejection, lookup_keys, plan_import
from app.repositories import candidates as candidate_repo


class InvalidImportFile(ValueError):
    """The file as a whole can't be imported; no row has been processed."""


@dataclass(frozen=True)
class ImportReport:
    imported: int
    merged: int
    rejected: list[Rejection]
    merges: list[Merge]


def parse_csv(data: bytes) -> list[ImportRow]:
    try:
        text = data.decode("utf-8-sig")  # tolerates an Excel byte-order mark
    except UnicodeDecodeError as exc:
        raise InvalidImportFile("file is not valid UTF-8") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    # enumerate counts CSV records, so a multi-line note doesn't shift row numbers.
    return [ImportRow(row=number, values=record) for number, record in enumerate(reader, start=1)]


async def import_candidates(owner_engine: AsyncEngine, data: bytes) -> ImportReport:
    rows = parse_csv(data)
    emails, legacy_ids = lookup_keys(rows)

    # One transaction for the whole import: it succeeds or fails as a whole.
    async with owner_connection(owner_engine) as conn:
        existing = await candidate_repo.find_existing(conn, emails, legacy_ids)
        plan = plan_import(rows, existing)
        await candidate_repo.insert_many(conn, plan.new_candidates)

    return ImportReport(
        imported=len(plan.new_candidates),
        merged=len(plan.merges),
        rejected=plan.rejections,
        merges=plan.merges,
    )
