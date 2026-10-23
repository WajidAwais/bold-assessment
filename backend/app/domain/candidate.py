"""The Candidate model and its canonical vocabularies. Pure Python, no I/O.

Walking-skeleton rules only: values are trimmed, blanks become null, emails are
lowercased, and Region/status must already be (case-insensitively) canonical.
The full normalization rules arrive in ticket 03.
"""

import re
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


def _region_key(code: str) -> str:
    """Fold case, whitespace and separators: ``us-mw``, `` CO-BOG ``, ``USW``."""
    return re.sub(r"[\s_-]", "", code).upper()


_REGIONS_BY_KEY = {_region_key(region): region for region in Region}


class Status(StrEnum):
    ACTIVE = "active"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    WITHDRAWN = "withdrawn"


_MONTHS = {
    name: number
    for number, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})", re.ASCII)  # YYYY-MM-DD
_US_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})", re.ASCII)  # MM/DD/YYYY
_TEXT_DATE = re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", re.ASCII)  # DD-Mon-YYYY


def parse_applied_date(value: str) -> date:
    """Read one of the three legacy date formats; raise ValueError otherwise.

    Impossible dates (``2026-02-30``) raise too: ``date()`` checks the calendar.
    """
    if match := _ISO_DATE.fullmatch(value):
        year, month, day = match.groups()
        return date(int(year), int(month), int(day))
    if match := _US_DATE.fullmatch(value):
        month, day, year = match.groups()
        return date(int(year), int(month), int(day))
    if (match := _TEXT_DATE.fullmatch(value)) and match[2].lower() in _MONTHS:
        day, month_name, year = match.groups()
        return date(int(year), _MONTHS[month_name.lower()], int(day))
    raise ValueError("not a YYYY-MM-DD, MM/DD/YYYY or DD-Mon-YYYY date")


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
    def _match_region(cls, value: Any) -> Any:
        # Exact match after folding; anything unmatched is left for the enum to reject.
        if isinstance(value, str):
            return _REGIONS_BY_KEY.get(_region_key(value), value)
        return value

    @field_validator("status", mode="before")
    @classmethod
    def _lowercase_status(cls, value: Any) -> Any:
        return value.lower() if isinstance(value, str) else value

    @field_validator("applied_date", mode="before")
    @classmethod
    def _legacy_date(cls, value: Any) -> Any:
        return parse_applied_date(value) if isinstance(value, str) else value

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
