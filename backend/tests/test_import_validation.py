"""HTTP seam: validation, Rejections, file guards and hostile content on import."""

import httpx
from sqlalchemy import func, select

from app.db.tables import candidates

AS_ADMIN = {"X-Recruiter-Id": "R-101"}

HEADER = (
    "candidate_id,first_name,last_name,email,phone,region_code,desired_role,"
    "salary_expectation,applied_date,status,source,notes"
)
ROW_C1001 = (
    'C-1001,Alicia,Trent,alicia.trent@gmail.com,+1 (734) 555-0142,US-MW,'
    'Full-Stack Engineer,"$95,000",2026-05-14,Active,LinkedIn,Strong React portfolio'
)
ROW_C1037 = (
    "C-1037,Dana,Whitlock,dana.whitlock@gmail.com,702-555-0163,US-W,"
    "Frontend Engineer,87000,2026-06-29,Active,Indeed,' OR '1'='1"
)
DROP_PAYLOAD = "O'Connor'); DROP TABLE candidates;--"


async def _import(client: httpx.AsyncClient, csv_bytes: bytes) -> httpx.Response:
    return await client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates_import.csv", csv_bytes, "text/csv")},
    )


async def _stored_notes(app, legacy_id: str) -> str | None:
    # No endpoint returns notes (the list leaves them out on purpose).
    async with app.state.owner_engine.connect() as conn:
        return await conn.scalar(
            select(candidates.c.notes).where(candidates.c.legacy_id == legacy_id)
        )


async def _candidate_count(app) -> int:
    async with app.state.owner_engine.connect() as conn:
        return await conn.scalar(select(func.count()).select_from(candidates))


# --- Rejections from the real export ---------------------------------------


async def test_the_real_export_rejects_each_invalid_row_with_every_reason(
    client, candidates_csv
):
    report = (await _import(client, candidates_csv)).json()

    validation_rejections = [
        (r["row"], r["candidate_id"], r["reason"])
        for r in report["rejected"]
        # Ticket 04 replaces the interim duplicate rule with Merge / ID Collision.
        if r["reason"] != "duplicate candidate"
    ]
    assert validation_rejections == [
        (34, "C-1033", "invalid email"),
        (35, "C-1034", "invalid email"),
        (36, "C-1035", "missing email"),
        (37, "C-1036", "invalid characters in last_name"),
        (41, "C-1040", "invalid date"),
        (46, "C-1045", "unknown region"),
        (48, "C-1047", "unknown status"),
        (49, "C-1048", "unknown status"),
        (53, "C-1051", "missing region_code"),
    ]
    assert report["imported"] == 40


async def test_normalized_rows_from_the_real_export_are_imported(client, candidates_csv):
    await _import(client, candidates_csv)

    listing = (await client.get("/api/v1/candidates", params={"page_size": 100}, headers=AS_ADMIN)).json()
    by_id = {item["legacy_id"]: item for item in listing["items"]}
    assert by_id["C-1042"]["region"] == "US-MW"  # us-mw
    assert by_id["C-1043"]["region"] == "CO-BOG"  # " CO-BOG "
    assert by_id["C-1044"]["region"] == "US-W"  # USW
    assert by_id["C-1046"]["status"] == "active"  # ACTIVE
    assert by_id["C-1038"]["applied_date"] == "2026-06-30"  # 06/30/2026
    assert by_id["C-1039"]["applied_date"] == "2026-05-14"  # 14-May-2026
    assert by_id["C-1041"]["applied_date"] is None
    assert "C-1050" in by_id  # the multi-line note didn't shift or break the row


# --- Hostile content -------------------------------------------------------


async def test_sql_looking_notes_round_trip_unchanged(client, app):
    response = await _import(client, "\n".join([HEADER, ROW_C1037]).encode())

    assert response.json()["imported"] == 1
    assert await _stored_notes(app, "C-1037") == "' OR '1'='1"


async def test_the_candidates_table_survives_the_real_export(client, app, candidates_csv):
    report = (await _import(client, candidates_csv)).json()

    assert await _candidate_count(app) == report["imported"]
    listing = await client.get("/api/v1/candidates", headers=AS_ADMIN)
    assert listing.status_code == 200


async def test_a_drop_table_payload_in_notes_is_stored_inertly(client, app):
    # C-1036's DROP payload moved from last_name (where it is rejected) into notes
    row = (
        "C-1036,Robert,O'Connor,robert.oconnor@gmail.com,(508) 555-0121,US-NE,"
        f'Full-Stack Engineer,101000,2026-06-26,Active,LinkedIn,"{DROP_PAYLOAD}"'
    )
    response = await _import(client, "\n".join([HEADER, ROW_C1001, row]).encode())

    assert response.json()["imported"] == 2
    assert await _stored_notes(app, "C-1036") == DROP_PAYLOAD
    assert await _candidate_count(app) == 2


# --- File guards -----------------------------------------------------------


async def test_a_file_that_is_not_utf8_is_refused(client, app):
    latin1 = "\n".join([HEADER, ROW_C1001.replace("Alicia", "Tomás")]).encode("latin-1")

    response = await _import(client, latin1)

    assert response.status_code == 400
    assert "UTF-8" in response.json()["detail"]
    assert await _candidate_count(app) == 0


async def test_a_byte_order_mark_is_tolerated(client):
    with_bom = "\n".join([HEADER, ROW_C1001]).encode("utf-8-sig")

    response = await _import(client, with_bom)

    assert response.status_code == 200
    assert response.json()["imported"] == 1


async def test_a_file_missing_expected_columns_is_refused_naming_them(client, app):
    header = HEADER.replace(",region_code", "").replace(",status", "")
    row = ROW_C1001.replace(",US-MW", "").replace(",Active", "")

    response = await _import(client, "\n".join([header, row]).encode())

    assert response.status_code == 400
    assert response.json()["detail"] == "missing columns: region_code, status"
    assert await _candidate_count(app) == 0


async def test_extra_columns_are_ignored(client):
    header = HEADER + ",favourite_colour"
    row = ROW_C1001 + ",teal"

    response = await _import(client, "\n".join([header, row]).encode())

    assert response.status_code == 200
    assert response.json()["imported"] == 1


async def test_an_empty_file_is_refused(client):
    response = await _import(client, b"")

    assert response.status_code == 400
    assert response.json()["detail"].startswith("missing columns: candidate_id, ")


async def test_a_file_over_5_mb_is_refused(client, app):
    padding = "x" * (5 * 1024 * 1024)
    oversized = "\n".join([HEADER, ROW_C1001.replace("Strong React portfolio", padding)])

    response = await _import(client, oversized.encode())

    assert response.status_code == 413
    assert await _candidate_count(app) == 0


async def test_a_file_of_exactly_5_mb_is_accepted(client):
    without_note = "\n".join([HEADER, ROW_C1001.replace("Strong React portfolio", "")]) + "\n"
    note = "x" * (5 * 1024 * 1024 - len(without_note.encode()))
    exact = ("\n".join([HEADER, ROW_C1001.replace("Strong React portfolio", note)]) + "\n").encode()
    assert len(exact) == 5 * 1024 * 1024

    response = await _import(client, exact)

    assert response.status_code == 200
    assert response.json()["imported"] == 1
