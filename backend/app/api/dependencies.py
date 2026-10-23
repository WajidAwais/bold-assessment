from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services import recruiter_service


def get_owner_engine(request: Request) -> AsyncEngine:
    """The table owner. Only the import may use it (ADR-0002)."""
    return request.app.state.owner_engine


def get_app_engine(request: Request) -> AsyncEngine:
    """``techforce_app``: non-owner, no BYPASSRLS. Every read uses it."""
    return request.app.state.app_engine


OwnerEngine = Annotated[AsyncEngine, Depends(get_owner_engine)]
AppEngine = Annotated[AsyncEngine, Depends(get_app_engine)]


async def get_current_recruiter_id(
    app_engine: AppEngine,
    x_recruiter_id: Annotated[str | None, Header()] = None,
) -> str:
    """Resolve ``X-Recruiter-Id``: missing is 401, unknown is 403."""
    if not x_recruiter_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Recruiter-Id header is required")
    recruiter = await recruiter_service.find_recruiter(app_engine, x_recruiter_id)
    if recruiter is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown recruiter")
    return recruiter["id"]


CurrentRecruiterId = Annotated[str, Depends(get_current_recruiter_id)]
