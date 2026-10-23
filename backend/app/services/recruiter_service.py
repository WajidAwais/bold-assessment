"""Recruiter roster reads: the switcher, and resolving who is asking."""

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import roster_connection
from app.repositories import recruiters as recruiter_repo


async def list_recruiters(app_engine: AsyncEngine) -> list[RowMapping]:
    async with roster_connection(app_engine) as conn:
        return await recruiter_repo.list_all(conn)


async def find_recruiter(app_engine: AsyncEngine, recruiter_id: str) -> RowMapping | None:
    async with roster_connection(app_engine) as conn:
        return await recruiter_repo.find(conn, recruiter_id)
