"""Recruiter roster reads, used to populate the Recruiter switcher."""

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.connections import unscoped_read_connection
from app.repositories import recruiters as recruiter_repo


async def list_recruiters(engine: AsyncEngine) -> list[RowMapping]:
    async with unscoped_read_connection(engine) as conn:
        return await recruiter_repo.list_all(conn)
