"""HTTP seam: only an Admin may import, because a Merge can fill blanks on existing Candidates."""

import pytest

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
ROW = "C-1041,Petra,Novak,petra.novak@gmail.com,(602) 555-0197,US-W,QA Engineer,80000,,Active,Careers page,"
CSV_BYTES = f"{HEADER}\n{ROW}".encode("utf-8")


async def _import(client, headers: dict[str, str]):
    return await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", CSV_BYTES, "text/csv")},
        headers=headers,
    )


async def test_an_admin_can_import(client):
    response = await _import(client, {"X-Recruiter-Id": "R-101"})

    assert response.status_code == 200
    assert response.json()["imported"] == 1


@pytest.mark.parametrize(
    ("headers", "expected_status"),
    [
        ({}, 401),
        ({"X-Recruiter-Id": "R-999"}, 403),
        ({"X-Recruiter-Id": "R-102"}, 403),
    ],
    ids=["missing header", "unknown recruiter", "non-admin recruiter"],
)
async def test_only_an_admin_can_import(client, headers, expected_status):
    response = await _import(client, headers)

    assert response.status_code == expected_status


async def test_a_refused_import_writes_nothing(client):
    await _import(client, {"X-Recruiter-Id": "R-102"})

    listing = await client.get("/api/v1/candidates", headers={"X-Recruiter-Id": "R-101"})
    assert listing.json()["total"] == 0
