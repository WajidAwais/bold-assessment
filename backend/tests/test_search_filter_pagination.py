"""HTTP seam: a Recruiter narrows their scoped list with search and status, and pages it.

Every assertion goes through ``GET /api/v1/candidates``; search, filter and
paging all run in SQL under forced RLS, so they can only narrow a Scope.
"""

import httpx
import pytest

CALEB = "R-102"
MARISOL = "R-103"
DANA = "R-101"

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
# Real rows from candidates_import.csv.
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


@pytest.fixture
async def candidates(client: httpx.AsyncClient) -> None:
    csv_bytes = "\n".join([HEADER, *ROWS]).encode("utf-8")
    response = await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
        headers={"X-Recruiter-Id": "R-101"},
    )
    assert response.json()["imported"] == len(ROWS)


async def _list(client: httpx.AsyncClient, recruiter_id: str, **params) -> httpx.Response:
    return await client.get(
        "/api/v1/candidates", params=params, headers={"X-Recruiter-Id": recruiter_id}
    )


def _ids(response: httpx.Response) -> list[str]:
    return [item["legacy_id"] for item in response.json()["items"]]


# --- Search -------------------------------------------------------------------


async def test_caleb_searching_for_a_ph_mnl_name_gets_nothing(candidates, client):
    as_dana = await _list(client, DANA, search="Hoa")
    as_caleb = await _list(client, CALEB, search="Hoa")

    assert _ids(as_dana) == ["C-1008"]
    assert as_caleb.status_code == 200
    assert as_caleb.json()["items"] == []
    assert as_caleb.json()["total"] == 0


@pytest.mark.parametrize(
    ("search", "expected"),
    [
        ("trent", ["C-1001"]),  # last name, case-insensitive
        ("ALICIA", ["C-1001"]),  # first name
        ("Alicia Trent", ["C-1001"]),  # full name
        ("MUELLER@gmail", ["C-1015"]),  # email
        ("backend eng", ["C-1015"]),  # desired role
        ("MÜLLER", ["C-1015"]),  # case folding beyond ASCII
    ],
)
async def test_search_matches_names_email_and_role_case_insensitively(
    candidates, client, search, expected
):
    assert _ids(await _list(client, DANA, search=search)) == expected


async def test_search_is_accent_sensitive(candidates, client):
    # Not "Tomas": tomas.herrera@gmail.com would rightly match by email.
    assert _ids(await _list(client, DANA, search="Müller")) == ["C-1015"]
    assert _ids(await _list(client, DANA, search="Muller")) == []


@pytest.mark.parametrize("wildcard", ["%", "_", "\\", "%%", "a%e"])
async def test_like_wildcards_in_search_match_only_themselves(candidates, client, wildcard):
    response = await _list(client, DANA, search=wildcard)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


async def test_the_c1036_drop_payload_in_search_returns_normally_and_harms_nothing(
    candidates, client
):
    payload = "O'Connor'); DROP TABLE candidates;--"

    response = await _list(client, DANA, search=payload)

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 25}
    assert (await _list(client, DANA)).json()["total"] == len(ROWS)


# --- Status filter --------------------------------------------------------------


@pytest.mark.parametrize("status", ["interviewing", "INTERVIEWING", "Interviewing"])
async def test_status_filter_matches_case_insensitively(candidates, client, status):
    response = await _list(client, DANA, status=status)

    assert _ids(response) == ["C-1008"]
    assert response.json()["total"] == 1


async def test_status_filter_and_search_combine_within_scope(candidates, client):
    response = await _list(client, MARISOL, status="active", search="engineer")

    assert _ids(response) == ["C-1006"]
    assert response.json()["total"] == 1


@pytest.mark.parametrize("status", ["actve", "on hold", "", "active'--"])
async def test_an_invalid_status_is_a_validation_error(candidates, client, status):
    response = await _list(client, DANA, status=status)

    assert response.status_code == 422


# --- Pagination and the scoped total -------------------------------------------


def _row(legacy_id: str, region: str, applied_date: str) -> str:
    n = legacy_id.removeprefix("C-")
    last_name = "".join("abcdefghij"[int(digit)] for digit in n).title()  # names are letters only
    return (
        f"{legacy_id},Pat,{last_name},pat.{n}@gmail.com,,{region},"
        f"QA Engineer,,{applied_date},active,,"
    )


async def _import(client: httpx.AsyncClient, rows: list[str]) -> None:
    csv_bytes = "\n".join([HEADER, *rows]).encode("utf-8")
    response = await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
        headers={"X-Recruiter-Id": "R-101"},
    )
    assert response.json()["imported"] == len(rows)


async def test_pages_are_ordered_newest_first_with_blank_dates_last_then_by_id(client):
    await _import(
        client,
        [
            _row("C-2001", "US-MW", "2026-06-01"),
            _row("C-2002", "US-NE", ""),
            _row("C-2003", "US-MW", "2026-06-10"),
            _row("C-2004", "US-NE", "2026-06-01"),
            _row("C-2005", "US-MW", ""),
            _row("C-2006", "PH-MNL", "2026-07-01"),  # newest, but outside Caleb's Scope
        ],
    )

    pages = [await _list(client, CALEB, page=page, page_size=2) for page in (1, 2, 3, 4)]

    assert [_ids(page) for page in pages] == [
        ["C-2003", "C-2001"],
        ["C-2004", "C-2002"],
        ["C-2005"],
        [],
    ]
    assert [page.json()["total"] for page in pages] == [5, 5, 5, 5]
    assert [(page.json()["page"], page.json()["page_size"]) for page in pages] == [
        (1, 2),
        (2, 2),
        (3, 2),
        (4, 2),
    ]


async def test_page_size_defaults_to_25_and_total_counts_the_whole_scope(client):
    await _import(client, [_row(f"C-{3000 + i}", "US-MW", "") for i in range(30)])
    await _import(client, [_row(f"C-{4000 + i}", "CO-BOG", "") for i in range(3)])

    first = (await _list(client, CALEB)).json()
    second = (await _list(client, CALEB, page=2)).json()

    assert (len(first["items"]), first["total"], first["page_size"]) == (25, 30, 25)
    assert (len(second["items"]), second["total"]) == (5, 30)
    assert (await _list(client, MARISOL)).json()["total"] == 3


async def test_total_counts_only_what_search_and_status_leave(candidates, client):
    body = (await _list(client, DANA, search="full-stack", page_size=1)).json()

    assert len(body["items"]) == 1
    assert body["total"] == 2  # C-1001 and C-1006


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101}, {"page": "x"}],
)
async def test_out_of_range_paging_is_a_validation_error(candidates, client, params):
    response = await _list(client, DANA, **params)

    assert response.status_code == 422


async def test_page_size_100_is_allowed(candidates, client):
    response = await _list(client, DANA, page_size=100)

    assert response.status_code == 200
    assert response.json()["page_size"] == 100
