"""Candidate reads. The single seam every Candidate read goes through.

Temporarily unscoped: ticket 02 adds the Recruiter and the scoped connection.
"""

from dataclasses import dataclass

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import unscoped_read_connection
from app.repositories import candidates as candidate_repo


@dataclass(frozen=True)
class CandidatePage:
    items: list[RowMapping]
    total: int
    page: int
    page_size: int


async def list_candidates(engine: AsyncEngine, *, page: int, page_size: int) -> CandidatePage:
    async with unscoped_read_connection(engine) as conn:
        items, total = await candidate_repo.list_page(
            conn, limit=page_size, offset=(page - 1) * page_size
        )
    return CandidatePage(items=items, total=total, page=page, page_size=page_size)
