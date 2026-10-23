"""HTTP seam: import a CSV, then list the Candidates it created."""

import httpx

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
# Real rows from candidates_import.csv
ROW_C1001 = (
    'C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,'
    'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio'
)
ROW_C1008 = (
    "C-1008,Nguyễn,Thị Hoa,hoa.nguyen@gmail.com,+63 905 555 0161,PH-MNL,"
    "Frontend Engineer,48000,2026-05-25,Interviewing,Referral,"
    "Unicode name — display must not mangle"
)


async def _import(client: httpx.AsyncClient, csv_bytes: bytes) -> httpx.Response:
    return await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
    )


async def test_imported_rows_are_listed_as_candidates(client):
    csv_bytes = "\n".join([HEADER, ROW_C1001, ROW_C1008]).encode("utf-8")

    response = await _import(client, csv_bytes)

    assert response.status_code == 200
    assert response.json() == {"imported": 2, "merged": 0, "rejected": [], "merges": []}

    listing = await client.get("/api/v1/candidates")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 25
    hoa, alicia = body["items"]  # newest applied date first
    assert {k: v for k, v in hoa.items() if k != "id"} == {
        "legacy_id": "C-1008",
        "first_name": "Nguyễn",
        "last_name": "Thị Hoa",
        "email": "hoa.nguyen@gmail.com",
        "region": "PH-MNL",
        "desired_role": "Frontend Engineer",
        "status": "interviewing",
        "applied_date": "2026-05-25",
    }
    assert alicia["legacy_id"] == "C-1001"
    assert isinstance(hoa["id"], int)
