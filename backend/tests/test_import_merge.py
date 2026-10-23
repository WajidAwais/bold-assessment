"""HTTP seam: Merge, ID Collision and idempotent re-import of the real export."""

import httpx
from sqlalchemy import select

from app.db.tables import candidates

AS_ADMIN = {"X-Recruiter-Id": "R-101"}

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
# Real rows from candidates_import.csv
ROW_C1016 = (
    "C-1016,Amara,Diallo,amara.diallo@gmail.com,(917) 555-0125,US-NE,"
    'Full-Stack Engineer,"$108,000",2026-06-04,Active,Referral,'
)
ROW_C1032 = (
    "C-1032,A.,Diallo,amara.diallo@gmail.com,917-555-9999,US-NE,"
    'Full-Stack Engineer,"$110,000",2026-06-20,Active,Indeed,Which record wins?'
)

EXPECTED_MERGES = [
    {"row": 31, "candidate_id": "C-1004", "merged_into": "C-1004"},
    {"row": 32, "candidate_id": "C-1031", "merged_into": "C-1001"},
    {"row": 33, "candidate_id": "C-1032", "merged_into": "C-1016"},
]
EXPECTED_REJECTIONS = [
    {"row": 34, "candidate_id": "C-1033", "reason": "invalid email"},
    {"row": 35, "candidate_id": "C-1034", "reason": "invalid email"},
    {"row": 36, "candidate_id": "C-1035", "reason": "missing email"},
    {"row": 37, "candidate_id": "C-1036", "reason": "invalid characters in last_name"},
    {"row": 41, "candidate_id": "C-1040", "reason": "invalid date"},
    {"row": 46, "candidate_id": "C-1045", "reason": "unknown region"},
    {"row": 48, "candidate_id": "C-1047", "reason": "unknown status"},
    {"row": 49, "candidate_id": "C-1048", "reason": "unknown status"},
    {"row": 52, "candidate_id": "C-1010", "reason": "candidate_id collision"},
    {"row": 53, "candidate_id": "C-1051", "reason": "missing region_code"},
]


async def _import(client: httpx.AsyncClient, csv_bytes: bytes) -> dict:
    response = await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
        headers={"X-Recruiter-Id": "R-101"},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _listing(client: httpx.AsyncClient) -> dict:
    response = await client.get(
        "/api/v1/candidates", params={"page_size": 100}, headers=AS_ADMIN
    )
    return response.json()


async def test_the_real_export_gives_40_imported_3_merged_10_rejected(client, candidates_csv):
    report = await _import(client, candidates_csv)

    assert (report["imported"], report["merged"], len(report["rejected"])) == (40, 3, 10)
    assert report["merges"] == EXPECTED_MERGES
    assert report["rejected"] == EXPECTED_REJECTIONS

    listing = await _listing(client)
    assert listing["total"] == 40
    by_email = {item["email"]: item for item in listing["items"]}
    assert by_email["amara.diallo@gmail.com"]["first_name"] == "Amara"
    assert by_email["amara.diallo@gmail.com"]["legacy_id"] == "C-1016"
    # The collision did not overwrite Sofía, and Becca was not created.
    sofia = next(item for item in listing["items"] if item["legacy_id"] == "C-1010")
    assert (sofia["first_name"], sofia["last_name"]) == ("Sofía", "Cárdenas")
    assert "becca.storm@gmail.com" not in by_email


async def test_reimporting_the_real_export_changes_nothing(client, candidates_csv):
    await _import(client, candidates_csv)
    before = await _listing(client)

    report = await _import(client, candidates_csv)

    assert (report["imported"], report["merged"]) == (0, 43)
    assert report["rejected"] == EXPECTED_REJECTIONS
    assert await _listing(client) == before


async def test_a_later_import_fills_blanks_of_a_stored_candidate_but_never_overwrites(
    client, app
):
    await _import(client, f"{HEADER}\n{ROW_C1016}\n".encode())

    report = await _import(client, f"{HEADER}\n{ROW_C1032}\n".encode())

    assert report["merges"] == [{"row": 1, "candidate_id": "C-1032", "merged_into": "C-1016"}]
    # Notes and phone aren't in the list response, so read the stored row.
    async with app.state.owner_engine.connect() as conn:
        stored = (
            await conn.execute(
                select(candidates.c.first_name, candidates.c.phone, candidates.c.notes)
            )
        ).one()
    assert tuple(stored) == ("Amara", "(917) 555-0125", "Which record wins?")
