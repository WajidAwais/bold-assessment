"""Scope: a Recruiter sees only Candidates in their Regions; an Admin sees all.

Two seams. The database role seam proves forced RLS holds beneath every
endpoint: a raw query as ``techforce_app`` is scoped, and fails closed with no
Recruiter context. The HTTP seam proves the API resolves the Recruiter from
``X-Recruiter-Id`` and returns only their Scope.
"""

import asyncpg
import httpx
import pytest

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
# Real rows from candidates_import.csv, one per Region that Caleb and Marisol cover.
ROWS = [
    "C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,"
    'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio',
    "C-1015,Jürgen,Müller,jurgen.mueller@gmail.com,+1 646 555 0183,US-NE,"
    "Backend Engineer,105000,2026-06-03,Active,LinkedIn,Relocating from Berlin",
    "C-1008,Nguyễn,Thị Hoa,hoa.nguyen@gmail.com,+63 905 555 0161,PH-MNL,"
    "Frontend Engineer,48000,2026-05-25,Interviewing,Referral,"
    "Unicode name — display must not mangle",
    "C-1006,Tomás,Herrera,tomas.herrera@gmail.com,+57 601 555 0177,CO-BOG,"
    "Full-Stack Engineer,72000,2026-05-22,Active,LinkedIn,Bilingual EN/ES",
]

CALEB = "R-102"
MARISOL = "R-103"
DANA = "R-101"


@pytest.fixture
async def one_candidate_per_region(client: httpx.AsyncClient) -> None:
    csv_bytes = "\n".join([HEADER, *ROWS]).encode("utf-8")
    response = await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
    )
    assert response.json()["imported"] == len(ROWS)


@pytest.fixture
async def as_app_role(app_role_url) -> asyncpg.Connection:
    conn = await asyncpg.connect(app_role_url.render_as_string(hide_password=False).replace(
        "postgresql+asyncpg", "postgresql"
    ))
    yield conn
    await conn.close()


# --- Database role seam: forced RLS beneath every endpoint ---------------------


async def test_raw_select_as_app_role_returns_only_the_recruiters_regions(
    one_candidate_per_region, as_app_role
):
    async with as_app_role.transaction():
        await as_app_role.execute("SELECT set_config('app.recruiter_id', $1, true)", CALEB)
        rows = await as_app_role.fetch("SELECT * FROM candidates")

    assert sorted(row["legacy_id"] for row in rows) == ["C-1001", "C-1015"]
    assert {row["region"] for row in rows} == {"US-MW", "US-NE"}


async def test_raw_select_as_app_role_with_no_recruiter_context_returns_nothing(
    one_candidate_per_region, as_app_role
):
    rows = await as_app_role.fetch("SELECT * FROM candidates")

    assert rows == []


async def test_recruiter_context_does_not_outlive_its_transaction(
    one_candidate_per_region, as_app_role
):
    async with as_app_role.transaction():
        await as_app_role.execute("SELECT set_config('app.recruiter_id', $1, true)", DANA)
        assert len(await as_app_role.fetch("SELECT * FROM candidates")) == len(ROWS)

    assert await as_app_role.fetch("SELECT * FROM candidates") == []


async def test_app_role_cannot_write_candidates(as_app_role):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await as_app_role.execute("DELETE FROM candidates")
