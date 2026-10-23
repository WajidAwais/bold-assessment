"""Domain seam: the normalization and validation rules, driven by real CSV rows.

Pure, no I/O. Each case is a record taken verbatim from candidates_import.csv
(variants are marked) and run through ``parse_candidate``, the single entry
point that turns a raw CSV record into a Candidate or a Rejection.
"""

import csv
import io
from datetime import date

import pytest

from app.domain.candidate import Candidate
from app.domain.import_plan import ImportRow, Rejection, parse_candidate

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)


def parse(record: str, row: int = 1) -> Candidate | Rejection:
    (values,) = csv.DictReader(io.StringIO(f"{HEADER}\n{record}", newline=""))
    return parse_candidate(ImportRow(row=row, values=values))


def accepted(record: str) -> Candidate:
    result = parse(record)
    assert isinstance(result, Candidate), result
    return result


def rejected_reason(record: str) -> str:
    result = parse(record)
    assert isinstance(result, Rejection), result
    return result.reason


# --- Email -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "email"),
    [
        (
            "C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
            'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio',
            "alicia.trent@gmail.com",
        ),
        (
            "C-1031,Alicia,Trent,  Alicia.Trent@Gmail.com ,+1 (734) 555-0142,US-MW,"
            'Full-Stack Engineer,"$95,000",2026-05-14,Active,Indeed,Possible re-application',
            "alicia.trent@gmail.com",
        ),
    ],
)
def test_email_is_trimmed_and_lowercased(record, email):
    assert accepted(record).email == email


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (
            "C-1033,Marcus,Reed,marcus.reed[at]gmail.com,(213) 555-0144,US-W,"
            "Backend Engineer,100000,2026-06-25,Active,LinkedIn,",
            "invalid email",
        ),
        (
            "C-1034,Tina,Holloway,tina.holloway.gmail.com,813-555-0119,US-SE,"
            "QA Engineer,76000,2026-06-25,Screening,Indeed,No @ in email",
            "invalid email",
        ),
        (
            "C-1035,Bo,Lindqvist,,(312) 555-0177,US-MW,Data Engineer,98000,"
            "2026-06-26,Active,Referral,Email missing entirely",
            "missing email",
        ),
    ],
)
def test_bad_emails_are_rejected_never_repaired(record, reason):
    assert rejected_reason(record) == reason


# --- Region ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "region"),
    [
        (
            "C-1042,Gordon,Ferris,gordon.ferris@gmail.com,(816) 555-0149,us-mw,"
            "Full-Stack Engineer,88000,2026-07-01,Active,LinkedIn,Lowercase region",
            "US-MW",
        ),
        (
            "C-1043,Lucía,Pardo,lucia.pardo@gmail.com,+57 300 555 0195, CO-BOG ,"
            "Backend Engineer,68000,2026-07-02,Active,Referral,Whitespace region",
            "CO-BOG",
        ),
        (
            "C-1044,Wesley,Trần,wesley.tran@gmail.com,(714) 555-0186,USW,"
            "Frontend Engineer,98000,2026-07-02,Active,Indeed,Missing hyphen in region",
            "US-W",
        ),
        (  # variant of C-1007: underscore separator
            "C-1007,Grace,Lim,grace.lim@gmail.com,+63 917 555 0122,ph_mnl,"
            "QA Engineer,45000,2026-05-23,Active,JobStreet,",
            "PH-MNL",
        ),
    ],
)
def test_region_ignores_case_whitespace_and_separators(record, region):
    assert accepted(record).region == region


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (
            "C-1045,Ingrid,Solberg,ingrid.solberg@gmail.com,(651) 555-0113,ZZ-99,"
            "Data Engineer,99000,2026-07-06,Active,LinkedIn,Region not in reference list",
            "unknown region",
        ),
        (
            "C-1051,Ivan,Petrov,ivan.petrov@gmail.com,,,Full-Stack Engineer,96000,"
            '2026-07-15,Active,LinkedIn,"No phone, no region"',
            "missing region_code",
        ),
    ],
)
def test_unknown_or_missing_regions_are_rejected(record, reason):
    assert rejected_reason(record) == reason


# --- Status ----------------------------------------------------------------


def test_status_is_matched_case_insensitively():
    record = (
        "C-1046,Barry,Quill,barry.quill@gmail.com,(614) 555-0175,US-MW,Full-Stack Engineer,"
        '85k,2026-07-07,ACTIVE,Indeed,"Uppercase status, salary as 85k"'
    )
    assert accepted(record).status == "active"


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (
            "C-1047,Renee,Ashford,renee.ashford@gmail.com,(919) 555-0130,US-SE,"
            "Backend Engineer,negotiable,2026-07-08,actve,LinkedIn,Misspelled status",
            "unknown status",
        ),
        (
            "C-1048,Victor,Hale,victor.hale@gmail.com,(212) 555-0159,US-NE,"
            "DevOps Engineer,,2026-07-09,on hold,Referral,Status not in enum",
            "unknown status",
        ),
        (  # variant of C-1048: status blank
            "C-1048,Victor,Hale,victor.hale@gmail.com,(212) 555-0159,US-NE,"
            "DevOps Engineer,,2026-07-09,,Referral,Status not in enum",
            "missing status",
        ),
    ],
)
def test_unknown_statuses_are_rejected_not_corrected(record, reason):
    assert rejected_reason(record) == reason


# --- Applied date ----------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "applied"),
    [
        (
            "C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
            'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio',
            date(2026, 5, 14),
        ),
        (
            "C-1038,Hank,Boseman,hank.boseman@gmail.com,(216) 555-0136,US-MW,"
            "DevOps Engineer,95000,06/30/2026,Active,LinkedIn,US-format date",
            date(2026, 6, 30),
        ),
        (
            "C-1039,Yara,Abadi,yara.abadi@gmail.com,(347) 555-0128,US-NE,"
            "Backend Engineer,104000,14-May-2026,Screening,Referral,Text-format date",
            date(2026, 5, 14),
        ),
        (  # variant of C-1039: month name in upper case
            "C-1039,Yara,Abadi,yara.abadi@gmail.com,(347) 555-0128,US-NE,"
            "Backend Engineer,104000,14-MAY-2026,Screening,Referral,Text-format date",
            date(2026, 5, 14),
        ),
        (
            "C-1041,Petra,Novak,petra.novak@gmail.com,(602) 555-0197,US-W,"
            "QA Engineer,80000,,Active,Careers page,Date missing",
            None,
        ),
    ],
)
def test_applied_date_accepts_the_three_legacy_formats(record, applied):
    assert accepted(record).applied_date == applied


@pytest.mark.parametrize(
    "applied",
    [
        "2026-02-30",  # C-1040, impossible calendar date
        "30/06/2026",  # day-first is not accepted
        "2026/05/14",
        "14-Mai-2026",
        "1747180800",  # Pydantic would otherwise read a Unix timestamp
    ],
)
def test_impossible_or_unknown_dates_are_rejected(applied):
    record = (
        "C-1040,Cole,Ramsey,cole.ramsey@gmail.com,904-555-0152,US-SE,"
        f"Full-Stack Engineer,90000,{applied},Active,Indeed,Impossible calendar date"
    )
    assert rejected_reason(record) == "invalid date"
