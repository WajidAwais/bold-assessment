"""Recruiter roster reads. SQLAlchemy Core only; the caller owns the transaction."""

from sqlalchemy import select
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection

from app.db.tables import recruiters


async def list_all(conn: AsyncConnection) -> list[RowMapping]:
    result = await conn.execute(
        select(
            recruiters.c.id,
            recruiters.c.full_name,
            recruiters.c.role,
            recruiters.c.regions,
        ).order_by(recruiters.c.id)
    )
    return list(result.mappings().all())


async def find(conn: AsyncConnection, recruiter_id: str) -> RowMapping | None:
    result = await conn.execute(
        select(
            recruiters.c.id,
            recruiters.c.full_name,
            recruiters.c.role,
            recruiters.c.regions,
        ).where(recruiters.c.id == recruiter_id)
    )
    return result.mappings().one_or_none()
