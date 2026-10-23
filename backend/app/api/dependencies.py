from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.recruiter import is_admin
from app.services import recruiter_service


def get_owner_engine(request: Request) -> AsyncEngine:
    """The table owner. Only the import may use it (ADR-0002)."""
    return request.app.state.owner_engine


def get_app_engine(request: Request) -> AsyncEngine:
    """``techforce_app``: non-owner, no BYPASSRLS. Every read uses it."""
    return request.app.state.app_engine


OwnerEngine = Annotated[AsyncEngine, Depends(get_owner_engine)]
AppEngine = Annotated[AsyncEngine, Depends(get_app_engine)]


async def get_current_recruiter(
    app_engine: AppEngine,
    x_recruiter_id: Annotated[str | None, Header()] = None,
) -> RowMapping:
    """Resolve ``X-Recruiter-Id`` to its roster row: missing is 401, unknown is 403.

    FastAPI caches a dependency per request, so the roster is read once even
    when several dependencies build on this one.
    """
    if not x_recruiter_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-Recruiter-Id header is required")
    recruiter = await recruiter_service.find_recruiter(app_engine, x_recruiter_id)
    if recruiter is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown recruiter")
    return recruiter


CurrentRecruiter = Annotated[RowMapping, Depends(get_current_recruiter)]


def get_current_recruiter_id(recruiter: CurrentRecruiter) -> str:
    return recruiter["id"]


CurrentRecruiterId = Annotated[str, Depends(get_current_recruiter_id)]


def require_admin(recruiter: CurrentRecruiter) -> str:
    """The current Recruiter's ID, or 403 unless they are an Admin."""
    if not is_admin(recruiter["role"]):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an Admin may import")
    return recruiter["id"]


AdminId = Annotated[str, Depends(require_admin)]
