from fastapi import APIRouter

from app.api.dependencies import AppEngine
from app.api.schemas import RecruiterOut
from app.services import recruiter_service

router = APIRouter(prefix="/api/v1/recruiters", tags=["recruiters"])


@router.get("", response_model=list[RecruiterOut])
async def list_recruiters(app_engine: AppEngine) -> list[RecruiterOut]:
    rows = await recruiter_service.list_recruiters(app_engine)
    return [RecruiterOut.model_validate(dict(row)) for row in rows]
