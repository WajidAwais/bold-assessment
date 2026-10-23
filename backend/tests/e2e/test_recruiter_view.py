"""Recruiter view smoke: Scope, rendering, search and status, as a user sees them."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def view_as(page: Page, recruiter_name: str) -> None:
    page.get_by_label("Viewing as").select_option(label=_option_label(page, recruiter_name))


def _option_label(page: Page, recruiter_name: str) -> str:
    option = page.get_by_label("Viewing as").locator("option", has_text=recruiter_name)
    return option.inner_text()


def expect_total(page: Page, total: int) -> None:
    """Wait for the scoped total; the leading "· " keeps 18 from passing for 8."""
    pager = page.get_by_role("navigation", name="Pagination")
    expect(pager).to_contain_text(f"· {total} candidates")


def region_cells(page: Page) -> list[str]:
    return page.get_by_role("row").locator("td:nth-child(3)").all_inner_texts()


def test_caleb_sees_only_us_mw_and_us_ne(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")

    expect_total(recruiter_view, 18)
    assert set(region_cells(recruiter_view)) == {"US-MW", "US-NE"}


def test_switching_to_marisol_leaves_none_of_calebs_rows(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")
    expect_total(recruiter_view, 18)
    expect(recruiter_view.get_by_role("cell", name="Alicia Trent")).to_have_count(1)

    view_as(recruiter_view, "Marisol Vega")

    expect_total(recruiter_view, 9)
    assert set(region_cells(recruiter_view)) == {"PH-MNL", "CO-BOG"}
    expect(recruiter_view.get_by_role("cell", name="Alicia Trent")).to_have_count(0)
    expect(recruiter_view.get_by_role("cell", name="Priya Raman")).to_have_count(0)


def test_vietnamese_name_renders_intact(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Marisol Vega")
    expect_total(recruiter_view, 9)

    expect(recruiter_view.get_by_role("cell", name="Nguyễn Thị Hoa", exact=True)).to_be_visible()


def name_cells(page: Page) -> list[str]:
    return page.get_by_role("row").locator("td:nth-child(1)").all_inner_texts()


def test_search_narrows_the_table(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")
    expect_total(recruiter_view, 18)

    recruiter_view.get_by_label("Search").fill("Raman")

    expect_total(recruiter_view, 1)
    assert name_cells(recruiter_view) == ["Priya Raman"]


def test_status_filter_narrows_the_table(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")
    expect_total(recruiter_view, 18)

    recruiter_view.get_by_label("Status").select_option("interviewing")

    expect_total(recruiter_view, 2)
    assert sorted(name_cells(recruiter_view)) == ["Priya Raman", "Trevor Nash"]
