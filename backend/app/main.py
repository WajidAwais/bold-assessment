from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import candidates, recruiters
from app.config import Settings
from app.db.connections import create_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.owner_engine.dispose()

    app = FastAPI(title="TechForce Recruiting Operations", lifespan=lifespan)
    # Engines connect lazily, so building the app never touches the database.
    app.state.owner_engine = create_engine(settings.database_url)
    app.include_router(candidates.router)
    app.include_router(recruiters.router)
    return app
