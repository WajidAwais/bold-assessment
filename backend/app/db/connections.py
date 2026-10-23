"""Engines and the connections each use case is allowed to use.

Every connection here opens a transaction that commits on success and rolls
back on error, so a use case either completes or leaves nothing behind.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

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
async def unscoped_read_connection(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """Temporary read transaction with no Recruiter context.

    Ticket 02 replaces this with a scoped connection that runs as
    ``techforce_app`` and sets ``app.recruiter_id`` inside the transaction.
    """
    async with engine.begin() as conn:
        yield conn
