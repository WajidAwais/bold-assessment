"""The Candidate model and its canonical vocabularies. Pure Python, no I/O.

Walking-skeleton rules only: values are trimmed, blanks become null, emails are
lowercased, and Region/status must already be (case-insensitively) canonical.
The full normalization rules arrive in ticket 03.
"""

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class Region(StrEnum):
    US_MW = "US-MW"
    US_NE = "US-NE"
    US_SE = "US-SE"
    US_W = "US-W"
    PH_MNL = "PH-MNL"
    CO_BOG = "CO-BOG"


class Status(StrEnum):
    ACTIVE = "active"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    WITHDRAWN = "withdrawn"


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    legacy_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    region: Region
    desired_role: str | None = None
    salary: int | None = None
    applied_date: date | None = None
    status: Status
    source: str | None = None
    notes: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def _lowercase_email(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value

    @field_validator("region", mode="before")
    @classmethod
    def _uppercase_region(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @field_validator("status", mode="before")
    @classmethod
    def _lowercase_status(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value

    @field_validator("salary", mode="before")
    @classmethod
    def _plain_integer_salary(cls, value: Any) -> Any:
        # Skeleton: only plain digits count; anything else is a soft null.
        if isinstance(value, str):
            return int(value) if value.isdigit() else None
        return value

    # Pydantic runs "before" validators in reverse definition order, so this
    # one, defined last, trims and nulls every field before the rules above.
    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_null(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
