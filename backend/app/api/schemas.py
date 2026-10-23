"""HTTP request/response models. The wire contract lives here."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class RejectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row: int
    candidate_id: str | None
    reason: str


class MergeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    row: int
    candidate_id: str | None
    merged_into: str


class ImportReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    imported: int
    merged: int
    rejected: list[RejectionOut]
    merges: list[MergeOut]


class CandidateListItem(BaseModel):
    """A row of the Recruiter table. Salary, phone and notes are left out on purpose."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    legacy_id: str
    first_name: str
    last_name: str
    email: str
    region: str
    desired_role: str | None
    status: str
    applied_date: date | None


class CandidateListOut(BaseModel):
    items: list[CandidateListItem]
    total: int
    page: int
    page_size: int


class RecruiterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    role: str
    regions: list[str]
