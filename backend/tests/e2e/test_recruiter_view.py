"""Recruiter view smoke: Scope, rendering, search and status, as a user sees them."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def view_as(page: Page, recruiter_name: str) -> None:
    page.get_by_label("Viewing as").select_option(label=_option_label(page, recruiter_name))


def _option_label(page: Page, recruiter_name: str) -> str:
    option = page.get_by_label("Viewing as").locator("option", has_text=recruiter_name)
    return option.inner_text()


def region_cells(page: Page) -> list[str]:
    return page.get_by_role("row").locator("td:nth-child(3)").all_inner_texts()


def test_caleb_sees_only_us_mw_and_us_ne(recruiter_view: Page) -> None:
    view_as(recruiter_view, "Caleb Nguyen")

    expect(recruiter_view.get_by_text("19 candidates")).to_be_visible()
    assert set(region_cells(recruiter_view)) == {"US-MW", "US-NE"}
