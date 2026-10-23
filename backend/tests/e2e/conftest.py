"""Recruiter view end-to-end harness (seam 4).

These tests drive the real UI in a browser against the **running compose
stack** (UI on 127.0.0.1:5173, API on 127.0.0.1:8000). They are marked ``e2e``
and deselected by default; run them with:

    docker compose up -d --build
    cd backend && uv run playwright install chromium   # once
    uv run pytest -m e2e

If the stack isn't reachable the tests are skipped. Expected totals are read
from the API for the same Recruiter, so extra imports into the stack's database
don't break the suite. ``E2E_UI_URL`` and ``E2E_API_URL`` override the defaults.

Data setup is deterministic: the real CSV is imported through the API before
any assertion. Re-import is idempotent, so running the suite twice is safe.
"""

import os
from pathlib import Path

import httpx
import pytest

UI_URL = os.environ.get("E2E_UI_URL", "http://127.0.0.1:5173")
API_URL = os.environ.get("E2E_API_URL", "http://127.0.0.1:8000")
ADMIN_ID = "R-101"
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def _clean_candidates() -> None:
    """Override the API suite's per-test truncate: e2e uses the stack's database."""


@pytest.fixture(scope="session")
def imported_stack() -> None:
    try:
        httpx.get(UI_URL, timeout=5).raise_for_status()
        httpx.get(f"{API_URL}/api/v1/recruiters", timeout=5)
    except httpx.HTTPError as exc:
        pytest.skip(f"compose stack not reachable ({exc}); run `docker compose up -d`")
    response = httpx.post(
        f"{API_URL}/api/v1/candidates/import",
        headers={"X-Recruiter-Id": ADMIN_ID},
        files={"file": ("candidates_import.csv", (REPO_ROOT / "candidates_import.csv").read_bytes())},
        timeout=30,
    )
    response.raise_for_status()


@pytest.fixture
def recruiter_view(imported_stack, page):
    page.goto(UI_URL)
    return page
