from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.api.dependencies import AppEngine, CurrentRecruiterId, OwnerEngine
from app.api.schemas import CandidateListItem, CandidateListOut, ImportReportOut
from app.services import candidate_service, import_service

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


@router.post("/import", response_model=ImportReportOut)
async def import_candidates(file: UploadFile, owner_engine: OwnerEngine) -> ImportReportOut:
    # Read one byte past the limit: enough to tell "too large" without reading it all.
    data = await file.read(import_service.MAX_IMPORT_BYTES + 1)
    try:
        report = await import_service.import_candidates(owner_engine, data)
    except import_service.ImportFileTooLarge as exc:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(exc)) from exc
    except import_service.InvalidImportFile as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return ImportReportOut.model_validate(report)


@router.get("", response_model=CandidateListOut)
async def list_candidates(
    app_engine: AppEngine,
    recruiter_id: CurrentRecruiterId,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> CandidateListOut:
    result = await candidate_service.list_candidates(
        app_engine, recruiter_id=recruiter_id, page=page, page_size=page_size
    )
    return CandidateListOut(
        items=[CandidateListItem.model_validate(dict(item)) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )
