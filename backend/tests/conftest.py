"""Test harness: a separate database on the compose Postgres.

The database name comes from ``TEST_DATABASE_NAME`` (default ``techforce_test``)
and is created if it doesn't exist, so parallel runs can each use their own.
Migrations run once per session; ``candidates`` is truncated before each test.
Transaction-rollback isolation is deliberately not used: later RLS tests need
committed rows seen through a different role.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url

from app.config import Settings
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


def _test_database_url() -> URL:
    database_name = os.environ.get("TEST_DATABASE_NAME", "techforce_test")
    return make_url(Settings().database_url).set(database=database_name)


async def _create_database_if_missing(url: URL) -> None:
    conn = await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", url.database
        )
        if not exists:
            # Identifiers can't be bound parameters; quote it ourselves.
            quoted = '"' + url.database.replace('"', '""') + '"'
            await conn.execute(f"CREATE DATABASE {quoted}")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    url = _test_database_url()
    asyncio.run(_create_database_if_missing(url))
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url", url.render_as_string(hide_password=False).replace("%", "%%")
    )
    command.upgrade(alembic_cfg, "head")
    return url


@pytest.fixture(scope="session")
async def app(test_database_url: URL):
    app = create_app(
        Settings(database_url=test_database_url.render_as_string(hide_password=False))
    )
    yield app
    await app.state.owner_engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_candidates(app) -> None:
    async with app.state.owner_engine.begin() as conn:
        await conn.execute(text("TRUNCATE candidates RESTART IDENTITY"))


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def candidates_csv() -> bytes:
    return (REPO_ROOT / "candidates_import.csv").read_bytes()
