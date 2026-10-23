"""Candidate persistence. SQLAlchemy Core only; the caller owns the transaction."""

import re
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import bindparam, func, insert, or_, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql.elements import ColumnElement

from app.db.tables import candidates
from app.domain.candidate import Candidate, Status
from app.domain.import_plan import FILLABLE_FIELDS, BlankFill

# Every Candidate field (the surrogate id is not part of the domain model).
CANDIDATE_COLUMNS = tuple(candidates.c[name] for name in Candidate.model_fields)

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
) -> list[Candidate]:
    """Fetch, in one query, every stored Candidate holding one of these emails
    or Legacy IDs."""
    if not emails and not legacy_ids:
        return []
    result = await conn.execute(
        select(*CANDIDATE_COLUMNS).where(
            or_(
                candidates.c.email.in_(list(emails)),
                candidates.c.legacy_id.in_(list(legacy_ids)),
            )
        )
    )
    return [Candidate.model_validate(dict(row)) for row in result.mappings()]


async def insert_many(conn: AsyncConnection, new_candidates: Sequence[Candidate]) -> None:
    """Insert all Candidates as one batched statement (no row-at-a-time writes)."""
    if not new_candidates:
        return
    await conn.execute(insert(candidates), [_to_row(c) for c in new_candidates])


async def fill_blanks(conn: AsyncConnection, fills: Sequence[BlankFill]) -> None:
    """Fill null fields of stored Candidates as one batched statement.

    ``COALESCE`` keeps any value already stored, so a fill can never overwrite.
    """
    if not fills:
        return
    statement = (
        update(candidates)
        .where(candidates.c.email == bindparam("match_email"))
        .values(
            {
                name: func.coalesce(
                    candidates.c[name], bindparam(f"fill_{name}", type_=candidates.c[name].type)
                )
                for name in FILLABLE_FIELDS
            }
        )
    )
    await conn.execute(
        statement,
        [
            {"match_email": fill.email}
            | {f"fill_{name}": fill.values.get(name) for name in FILLABLE_FIELDS}
            for fill in fills
        ],
    )


async def list_page(
    conn: AsyncConnection,
    *,
    search: str | None,
    status: Status | None,
    limit: int, offset: int
) -> tuple[list[RowMapping], int]:
    """One page of the Candidates visible on ``conn``, and how many match in all.

    Filters are plain WHERE clauses: RLS has already narrowed the table to the
    caller's Scope, so these can only narrow it further, and ``total`` counts
    the same filtered set.
    """
    conditions = _list_conditions(search=search, status=status)
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


def _list_conditions(
    *, search: str | None, status: Status | None
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if status is not None:
        conditions.append(candidates.c.status == status.value)
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
