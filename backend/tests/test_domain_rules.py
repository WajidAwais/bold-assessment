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


# --- Salary ----------------------------------------------------------------


def _with_salary(salary: str) -> str:
    # C-1001 with its salary swapped for the case under test
    return (
        "C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
        f"Full-Stack Engineer,{salary},2026-05-14,Active,LinkedIn,Strong React portfolio"
    )


@pytest.mark.parametrize(
    ("salary", "expected"),
    [
        ('"$95,000"', 95000),  # C-1001
        ('"97,500"', 97500),  # C-1004
        ("88000", 88000),  # C-1002
        ("85k", 85000),  # C-1046
        ("85K", 85000),
        ("negotiable", None),  # C-1047
        ("", None),  # C-1048
        ("0", None),  # not a positive integer
        ("-5000", None),
        ("95000.50", None),
    ],
)
def test_salary_becomes_a_whole_number_or_a_soft_null(salary, expected):
    assert accepted(_with_salary(salary)).salary == expected


# --- Names -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("record", "first_name", "last_name"),
    [
        (
            "C-1008,Nguyễn,Thị Hoa,hoa.nguyen@gmail.com,+63 905 555 0161,PH-MNL,"
            "Frontend Engineer,48000,2026-05-25,Interviewing,Referral,"
            "Unicode name — display must not mangle",
            "Nguyễn",
            "Thị Hoa",
        ),
        (
            "C-1006,Tomás,Herrera,tomas.herrera@gmail.com,+57 601 555 0177,CO-BOG,"
            "Full-Stack Engineer,72000,2026-05-22,Active,LinkedIn,Bilingual EN/ES",
            "Tomás",
            "Herrera",
        ),
        (
            "C-1015,Jürgen,Müller,jurgen.mueller@gmail.com,+1 646 555 0183,US-NE,"
            "Backend Engineer,105000,2026-06-03,Active,LinkedIn,Relocating from Berlin",
            "Jürgen",
            "Müller",
        ),
        (
            "C-1049,Maya,Castellanos-Ruiz,maya.cr@gmail.com,(505) 555-0141,US-W,"
            "Full-Stack Engineer,107000,2026-07-10,Active,Referral,"
            '"Prefers remote, but open to hybrid in Denver, CO"',
            "Maya",
            "Castellanos-Ruiz",
        ),
        (
            "C-1032,A.,Diallo,amara.diallo@gmail.com,917-555-9999,US-NE,"
            'Full-Stack Engineer,"$110,000",2026-06-20,Active,Indeed,Which record wins?',
            "A.",
            "Diallo",
        ),
        (  # variant of C-1036 with a real apostrophe name
            "C-1036,Robert,O'Connor,robert.oconnor@gmail.com,(508) 555-0121,US-NE,"
            "Full-Stack Engineer,101000,2026-06-26,Active,LinkedIn,",
            "Robert",
            "O'Connor",
        ),
        (  # variant of C-1006, decomposed: "a" + combining acute accent
            "C-1006,Tomás,Herrera,tomas.herrera@gmail.com,+57 601 555 0177,CO-BOG,"
            "Full-Stack Engineer,72000,2026-05-22,Active,LinkedIn,Bilingual EN/ES",
            "Tomás",
            "Herrera",
        ),
    ],
)
def test_names_in_any_script_are_accepted_and_nfc_normalized(record, first_name, last_name):
    candidate = accepted(record)
    assert (candidate.first_name, candidate.last_name) == (first_name, last_name)


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (
            "C-1036,Robert,O'Connor'); DROP TABLE candidates;--,robert.oconnor@gmail.com,"
            "(508) 555-0121,US-NE,Full-Stack Engineer,101000,2026-06-26,Active,LinkedIn,"
            "Classic injection probe in last_name",
            "invalid characters in last_name",
        ),
        (  # variant of C-1007: a digit in the first name
            "C-1007,Gr4ce,Lim,grace.lim@gmail.com,+63 917 555 0122,PH-MNL,"
            "QA Engineer,45000,2026-05-23,Active,JobStreet,",
            "invalid characters in first_name",
        ),
        (  # variant of C-1007: first name blank
            "C-1007,,Lim,grace.lim@gmail.com,+63 917 555 0122,PH-MNL,"
            "QA Engineer,45000,2026-05-23,Active,JobStreet,",
            "missing first_name",
        ),
        (  # variant of C-1007: a 101-character last name
            f"C-1007,Grace,{'L' * 101},grace.lim@gmail.com,+63 917 555 0122,PH-MNL,"
            "QA Engineer,45000,2026-05-23,Active,JobStreet,",
            "invalid last_name",
        ),
    ],
)
def test_names_with_non_name_characters_are_rejected(record, reason):
    assert rejected_reason(record) == reason


# --- Free-text fields ------------------------------------------------------


def test_free_text_fields_are_trimmed_and_otherwise_verbatim():
    # C-1050's multi-line note, with padding added around phone, role and source
    record = (
        "C-1050,Oliver,Grant,oliver.grant@gmail.com,  (802) 555-0168 ,US-NE,"
        " Data Engineer ,103000,2026-07-13,Active, LinkedIn ,\"Interview notes:\n"
        "Round 1 passed.\nRound 2 pending scheduling.\""
    )
    candidate = accepted(record)
    assert candidate.phone == "(802) 555-0168"
    assert candidate.desired_role == "Data Engineer"
    assert candidate.source == "LinkedIn"
    assert candidate.notes == "Interview notes:\nRound 1 passed.\nRound 2 pending scheduling."


def test_sql_looking_notes_are_kept_as_text():
    record = (
        "C-1037,Dana,Whitlock,dana.whitlock@gmail.com,702-555-0163,US-W,"
        "Frontend Engineer,87000,2026-06-29,Active,Indeed,' OR '1'='1"
    )
    assert accepted(record).notes == "' OR '1'='1"


# --- Rejections ------------------------------------------------------------


def test_a_rejection_lists_every_problem_in_column_order():
    # C-1033 with a bad name, region, date and status as well as its bad email
    record = (
        "C-1033,Marcus,Re;ed,marcus.reed[at]gmail.com,(213) 555-0144,ZZ-99,"
        "Backend Engineer,100000,2026-02-30,actve,LinkedIn,"
    )
    result = parse(record, row=34)
    assert result == Rejection(
        row=34,
        candidate_id="C-1033",
        reason=(
            "invalid characters in last_name; invalid email; unknown region; "
            "invalid date; unknown status"
        ),
    )


def test_a_row_without_a_legacy_id_is_rejected():
    record = (
        ",Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
        'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio'
    )
    result = parse(record, row=1)
    assert result == Rejection(row=1, candidate_id=None, reason="missing candidate_id")
