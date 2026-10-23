"""Recruiter view smoke: Scope, rendering, search and status, as a user sees them.

Expected totals come from the API for the same Recruiter and filters, never
from hard-coded counts, so the tests hold whatever else the stack's database
has been given.
"""

import httpx
import pytest
from playwright.sync_api import Page, expect

from tests.e2e.conftest import API_URL

pytestmark = pytest.mark.e2e


def recruiter_id(full_name: str) -> str:
    roster = httpx.get(f"{API_URL}/api/v1/recruiters", timeout=5).json()
    (match,) = [r["id"] for r in roster if r["full_name"] == full_name]
    return match


def api_listing(recruiter_name: str, **params: str) -> dict:
    """What the API returns to this Recruiter: the source of truth for the UI."""
    response = httpx.get(
        f"{API_URL}/api/v1/candidates",
        params={"page_size": "100", **params},
        headers={"X-Recruiter-Id": recruiter_id(recruiter_name)},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def view_as(page: Page, recruiter_name: str) -> int:
    """Switch to the Recruiter, wait for their scoped total, and return it."""
    page.get_by_label("Viewing as").select_option(label=_option_label(page, recruiter_name))
    total = api_listing(recruiter_name)["total"]
    expect_total(page, total)
    return total


def _option_label(page: Page, recruiter_name: str) -> str:
    option = page.get_by_label("Viewing as").locator("option", has_text=recruiter_name)
    return option.inner_text()


def expect_total(page: Page, total: int) -> None:
    """Wait for the scoped total; the leading "· " keeps 18 from passing for 8."""
    pager = page.get_by_role("navigation", name="Pagination")
    expect(pager).to_contain_text(f"· {total} candidates")


def region_cells(page: Page) -> list[str]:
    return page.get_by_role("row").locator("td:nth-child(3)").all_inner_texts()


def name_cells(page: Page) -> list[str]:
    return page.get_by_role("row").locator("td:nth-child(1)").all_inner_texts()


def full_names(listing: dict) -> list[str]:
    return sorted(f"{c['first_name']} {c['last_name']}" for c in listing["items"])


def test_caleb_sees_only_us_mw_and_us_ne(recruiter_view: Page) -> None:
    total = view_as(recruiter_view, "Caleb Nguyen")

    assert total > 0
    assert set(region_cells(recruiter_view)) == {"US-MW", "US-NE"}


def test_switching_to_marisol_leaves_none_of_calebs_rows(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")
    expect(recruiter_view.get_by_role("cell", name="Alicia Trent")).to_have_count(1)

    total = view_as(recruiter_view, "Marisol Vega")

    assert total > 0
    assert set(region_cells(recruiter_view)) == {"PH-MNL", "CO-BOG"}
    expect(recruiter_view.get_by_role("cell", name="Alicia Trent")).to_have_count(0)
    expect(recruiter_view.get_by_role("cell", name="Priya Raman")).to_have_count(0)


def test_vietnamese_name_renders_intact(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Marisol Vega")

    expect(recruiter_view.get_by_role("cell", name="Nguyễn Thị Hoa", exact=True)).to_be_visible()


def test_search_narrows_the_table(recruiter_view: Page) -> None:
    unfiltered = view_as(recruiter_view, "Caleb Nguyen")
    expected = api_listing("Caleb Nguyen", search="Raman")

    recruiter_view.get_by_label("Search").fill("Raman")

    assert 0 < expected["total"] < unfiltered
    expect_total(recruiter_view, expected["total"])
    assert "Priya Raman" in name_cells(recruiter_view)
    assert sorted(name_cells(recruiter_view)) == full_names(expected)


def test_status_filter_narrows_the_table(recruiter_view: Page) -> None:
    unfiltered = view_as(recruiter_view, "Caleb Nguyen")
    expected = api_listing("Caleb Nguyen", status="interviewing")

    recruiter_view.get_by_label("Status").select_option("interviewing")

    assert 0 < expected["total"] < unfiltered
    expect_total(recruiter_view, expected["total"])
    assert sorted(name_cells(recruiter_view)) == full_names(expected)
