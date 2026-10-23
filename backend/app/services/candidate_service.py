"""Candidate reads. The single seam every Candidate read goes through.

Reads run as ``techforce_app`` inside a transaction scoped to one Recruiter, so
forced RLS returns only that Recruiter's Scope (ADR-0002).
"""

from dataclasses import dataclass

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import scoped_connection
from app.repositories import candidates as candidate_repo


@dataclass(frozen=True)
class CandidatePage:
    items: list[RowMapping]
    total: int
    page: int
    page_size: int


async def list_candidates(
    app_engine: AsyncEngine,
    *,
    recruiter_id: str,
    search: str | None = None,
    page: int,
    page_size: int,
) -> CandidatePage:
    async with scoped_connection(app_engine, recruiter_id) as conn:
        items, total = await candidate_repo.list_page(
            conn, search=search, limit=page_size, offset=(page - 1) * page_size
        )
    return CandidatePage(items=items, total=total, page=page, page_size=page_size)
