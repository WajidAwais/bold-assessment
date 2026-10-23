"""Engines and the connections each use case is allowed to use.

Every connection here opens a transaction that commits on success and rolls
back on error, so a use case either completes or leaves nothing behind.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


@asynccontextmanager
async def owner_connection(owner_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """A transaction as the table owner, which sees every Candidate.

    Only the import may use this: Merge and ID Collision detection must see
    Candidates in every Region (ADR-0002). Any other caller is a red flag.
    """
    async with owner_engine.begin() as conn:
        yield conn


@asynccontextmanager
async def scoped_connection(
    app_engine: AsyncEngine, recruiter_id: str
) -> AsyncIterator[AsyncConnection]:
    """A read transaction as ``techforce_app`` that sees only the Recruiter's Scope.

    The Recruiter context is set with ``set_config(..., true)``: it is local to
    this transaction, so it can never leak to the next user of a pooled
    connection. Forced RLS on ``candidates`` does the scoping (ADR-0002).
    """
    async with app_engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.recruiter_id', :recruiter_id, true)"),
            {"recruiter_id": recruiter_id},
        )
        yield conn


@asynccontextmanager
async def roster_connection(app_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """A read transaction as ``techforce_app`` with no Recruiter context.

    For the Recruiter roster only. Candidates are invisible here: with no
    context the RLS policy admits no rows (fails closed).
    """
    async with app_engine.begin() as conn:
        yield conn
