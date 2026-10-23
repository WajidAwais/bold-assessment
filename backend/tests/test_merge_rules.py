"""Domain seam: first-seen Merge, blank-fill and ID Collision (ADR-0001).

Pure, no I/O. Rows are taken from candidates_import.csv (variants are marked)
and run through ``plan_import``, with what the database already holds passed
in as ``ExistingCandidates``.
"""

import csv
import io

from app.domain.candidate import Candidate
from app.domain.import_plan import (
    BlankFill,
    ExistingCandidates,
    ImportRow,
    Merge,
    Rejection,
    plan_import,
)

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)

ROW_C1001 = (
    "C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
    'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio'
)
ROW_C1031 = (
    "C-1031,Alicia,Trent,  Alicia.Trent@Gmail.com ,+1 (734) 555-0142,US-MW,"
    'Full-Stack Engineer,"$95,000",2026-05-14,Active,Indeed,Possible re-application'
)
ROW_C1016 = (
    "C-1016,Amara,Diallo,amara.diallo@gmail.com,(917) 555-0125,US-NE,"
    'Full-Stack Engineer,"$108,000",2026-06-04,Active,Referral,'
)
ROW_C1032 = (
    "C-1032,A.,Diallo,amara.diallo@gmail.com,917-555-9999,US-NE,"
    'Full-Stack Engineer,"$110,000",2026-06-20,Active,Indeed,Which record wins?'
)
ROW_C1010 = (
    "C-1010,Sofía,Cárdenas,sofia.cardenas@hotmail.com,+57 310 555 0148,CO-BOG,"
    "Backend Engineer,70000,2026-05-27,Screening,Referral,"
)
ROW_C1010_BECCA = (
    "C-1010,Becca,Storm,becca.storm@gmail.com,(414) 555-0176,US-MW,QA Engineer,"
    "74000,2026-07-14,Active,Indeed,Same ID as Sofía Cárdenas — ID collision"
)


def rows(*records: str) -> list[ImportRow]:
    reader = csv.DictReader(io.StringIO("\n".join([HEADER, *records]), newline=""))
    return [ImportRow(number, values) for number, values in enumerate(reader, start=1)]


def candidate(record: str) -> Candidate:
    (row,) = rows(record)
    return Candidate.model_validate(
        {
            "legacy_id": row.values["candidate_id"],
            "first_name": row.values["first_name"],
            "last_name": row.values["last_name"],
            "email": row.values["email"],
            "phone": row.values["phone"],
            "region": row.values["region_code"],
            "desired_role": row.values["desired_role"],
            "salary": row.values["salary_expectation"],
            "applied_date": row.values["applied_date"],
            "status": row.values["status"],
            "source": row.values["source"],
            "notes": row.values["notes"],
        }
    )


def test_a_later_row_with_the_same_email_merges_into_the_first_seen_candidate():
    plan = plan_import(rows(ROW_C1001, ROW_C1031), ExistingCandidates())

    assert [c.legacy_id for c in plan.new_candidates] == ["C-1001"]
    assert plan.merges == [Merge(row=2, candidate_id="C-1031", merged_into="C-1001")]
    assert plan.rejections == []


def test_a_merged_row_fills_only_the_blanks_of_the_first_seen_candidate():
    plan = plan_import(rows(ROW_C1016, ROW_C1032), ExistingCandidates())

    (amara,) = plan.new_candidates
    # First-seen values win, even over the degraded "A."
    assert (amara.legacy_id, amara.first_name, amara.phone, amara.salary, amara.source) == (
        "C-1016",
        "Amara",
        "(917) 555-0125",
        108000,
        "Referral",
    )
    # C-1016 had no notes, so C-1032's fill the blank.
    assert amara.notes == "Which record wins?"
    assert plan.merges == [Merge(row=2, candidate_id="C-1032", merged_into="C-1016")]


def test_a_new_person_reusing_anothers_legacy_id_is_an_id_collision():
    plan = plan_import(rows(ROW_C1010, ROW_C1010_BECCA), ExistingCandidates())

    assert [c.email for c in plan.new_candidates] == ["sofia.cardenas@hotmail.com"]
    assert plan.rejections == [
        Rejection(row=2, candidate_id="C-1010", reason="candidate_id collision")
    ]
    assert plan.merges == []


def test_email_wins_over_a_legacy_id_that_belongs_to_someone_else():
    # Variant: Alicia's email carrying Sofía's Legacy ID
    alicia_as_c1010 = ROW_C1031.replace("C-1031", "C-1010", 1)

    plan = plan_import(rows(ROW_C1001, ROW_C1010, alicia_as_c1010), ExistingCandidates())

    assert [c.legacy_id for c in plan.new_candidates] == ["C-1001", "C-1010"]
    assert plan.merges == [Merge(row=3, candidate_id="C-1010", merged_into="C-1001")]
    assert plan.rejections == []


# --- The database counts as first-seen -------------------------------------


def test_a_row_matching_a_stored_candidate_merges_into_it_and_creates_nothing():
    existing = ExistingCandidates([candidate(ROW_C1001)])

    plan = plan_import(rows(ROW_C1001, ROW_C1031), existing)

    assert plan.new_candidates == []
    assert plan.merges == [
        Merge(row=1, candidate_id="C-1001", merged_into="C-1001"),
        Merge(row=2, candidate_id="C-1031", merged_into="C-1001"),
    ]
    assert plan.blank_fills == []


def test_a_merge_into_a_stored_candidate_fills_only_its_blanks():
    existing = ExistingCandidates([candidate(ROW_C1016)])

    plan = plan_import(rows(ROW_C1032), existing)

    assert plan.new_candidates == []
    assert plan.blank_fills == [
        BlankFill(email="amara.diallo@gmail.com", values={"notes": "Which record wins?"})
    ]


def test_a_new_person_reusing_a_stored_legacy_id_is_an_id_collision():
    existing = ExistingCandidates([candidate(ROW_C1010)])

    plan = plan_import(rows(ROW_C1010_BECCA), existing)

    assert plan.new_candidates == []
    assert plan.rejections == [
        Rejection(row=1, candidate_id="C-1010", reason="candidate_id collision")
    ]


def test_planning_the_same_rows_against_their_own_result_changes_nothing():
    records = (ROW_C1001, ROW_C1016, ROW_C1010, ROW_C1031, ROW_C1032, ROW_C1010_BECCA)
    first = plan_import(rows(*records), ExistingCandidates())

    again = plan_import(rows(*records), ExistingCandidates(first.new_candidates))

    assert again.new_candidates == []
    assert again.blank_fills == []
    assert len(again.merges) == len(first.new_candidates) + len(first.merges)
    assert again.rejections == first.rejections
