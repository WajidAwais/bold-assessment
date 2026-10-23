"""The Candidate model and its canonical vocabularies. Pure Python, no I/O.

Validating a Candidate applies every normalization rule from the spec: values
are trimmed and blanks become null; emails are lowercased and must be valid;
Region and status are matched exactly after folding; dates come in one of three
legacy formats; salaries become whole numbers or a soft null; names are
NFC-normalized and allow-listed. Nothing is ever repaired by guessing.
"""

import re
import unicodedata
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator
from pydantic_core import PydanticCustomError


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


# Name characters beyond Unicode letters (L*) and combining marks (M*).
_NAME_PUNCTUATION = frozenset(" '-.")


def normalize_name(value: str) -> str:
    """NFC-normalize a name; raise if it holds anything but name characters."""
    value = unicodedata.normalize("NFC", value)
    for char in value:
        if char not in _NAME_PUNCTUATION and unicodedata.category(char)[0] not in "LM":
            raise PydanticCustomError("invalid_characters", "invalid characters in name")
    return value


_SALARY = re.compile(r"([0-9]+)([kK]?)")


def parse_salary(value: str) -> int | None:
    """``$95,000``, ``97,500``, ``85k`` -> whole numbers; anything else -> None."""
    match = _SALARY.fullmatch(re.sub(r"[$,\s]", "", value))
    if not match:
        return None
    amount = int(match[1]) * (1000 if match[2] else 1)
    return amount if amount > 0 else None


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    legacy_id: str
    first_name: Annotated[str, StringConstraints(max_length=100)]
    last_name: Annotated[str, StringConstraints(max_length=100)]
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
    def _salary(cls, value: Any) -> Any:
        # A soft field: an unreadable salary becomes null, never a Rejection.
        return parse_salary(value) if isinstance(value, str) else value

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _name(cls, value: Any) -> Any:
        return normalize_name(value) if isinstance(value, str) else value

    # Pydantic runs "before" validators in reverse definition order, so this
    # one, defined last, trims and nulls every field before the rules above.
    @field_validator("*", mode="before")
    @classmethod
    def _blank_is_null(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
