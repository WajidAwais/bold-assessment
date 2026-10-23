from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine


def get_owner_engine(request: Request) -> AsyncEngine:
    return request.app.state.owner_engine


OwnerEngine = Annotated[AsyncEngine, Depends(get_owner_engine)]
