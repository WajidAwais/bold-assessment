"""Candidate persistence. SQLAlchemy Core only; the caller owns the transaction."""

import re
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import func, insert, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.tables import candidates
from app.domain.candidate import Candidate
from app.domain.import_plan import ExistingCandidates

LIST_COLUMNS = (
    candidates.c.id,
    candidates.c.legacy_id,
    candidates.c.first_name,
    candidates.c.last_name,
    candidates.c.email,
    candidates.c.region,
    candidates.c.desired_role,
    candidates.c.status,
    candidates.c.applied_date,
)


async def find_existing(
    conn: AsyncConnection, emails: Collection[str], legacy_ids: Collection[str]
) -> ExistingCandidates:
    """Look up, in one query, which of these emails and Legacy IDs are taken."""
    if not emails and not legacy_ids:
        return ExistingCandidates()
    result = await conn.execute(
        select(candidates.c.email, candidates.c.legacy_id).where(
            or_(
                candidates.c.email.in_(list(emails)),
                candidates.c.legacy_id.in_(list(legacy_ids)),
            )
        )
    )
    rows = result.all()
    return ExistingCandidates(
        emails=frozenset(row.email for row in rows),
        legacy_ids=frozenset(row.legacy_id for row in rows),
    )


async def insert_many(conn: AsyncConnection, new_candidates: Sequence[Candidate]) -> None:
    """Insert all Candidates as one batched statement (no row-at-a-time writes)."""
    if not new_candidates:
        return
    await conn.execute(insert(candidates), [_to_row(c) for c in new_candidates])


async def list_page(
    conn: AsyncConnection, *, search: str | None, limit: int, offset: int
) -> tuple[list[RowMapping], int]:
    """One page of the Candidates visible on ``conn``, and how many match in all.

    Filters are plain WHERE clauses: RLS has already narrowed the table to the
    caller's Scope, so these can only narrow it further, and ``total`` counts
    the same filtered set.
    """
    conditions = _list_conditions(search=search)
    total = await conn.scalar(select(func.count()).select_from(candidates).where(*conditions))
    result = await conn.execute(
        select(*LIST_COLUMNS)
        .where(*conditions)
        .order_by(candidates.c.applied_date.desc().nulls_last(), candidates.c.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.mappings().all()), total or 0


_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    """Make ``%``, ``_`` and the escape character itself match literally."""
    return re.sub(r"([%_\\])", r"\\\1", term)


def _list_conditions(*, search: str | None) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if search:
        # Case-insensitive, accent-sensitive substring; the term is a bound
        # parameter, so SQL-looking text is only ever compared, never run.
        pattern = f"%{_escape_like(search)}%"
        full_name = candidates.c.first_name + " " + candidates.c.last_name
        conditions.append(
            or_(
                *(
                    column.ilike(pattern, escape=_LIKE_ESCAPE)
                    for column in (
                        candidates.c.first_name,
                        candidates.c.last_name,
                        full_name,
                        candidates.c.email,
                        candidates.c.desired_role,
                    )
                )
            )
        )
    return conditions


def _to_row(candidate: Candidate) -> dict[str, Any]:
    row = candidate.model_dump()
    row["region"] = candidate.region.value
    row["status"] = candidate.status.value
    return row
