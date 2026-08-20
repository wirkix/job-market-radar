"""Parses the real (saved) WWR detail-page HTML fixture, so a site redesign
that renames these CSS classes fails this test loudly instead of silently
returning None/None/None forever in production.
"""

from pathlib import Path

from bs4 import BeautifulSoup

from scraper.clean import parse_about_list
from scraper.fetch_detail import (
    _ABOUT_ITEM_SELECTOR,
    _COMPANY_NAME_SELECTOR,
    _TITLE_SELECTOR,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wwr_job_detail.html"


def _parse_fixture():
    soup = BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "html.parser")
    title_el = soup.select_one(_TITLE_SELECTOR)
    company_el = soup.select_one(_COMPANY_NAME_SELECTOR)
    about_texts = [li.get_text(" ", strip=True) for li in soup.select(_ABOUT_ITEM_SELECTOR)]
    return title_el, company_el, about_texts


def test_title_selector_finds_job_title():
    title_el, _, _ = _parse_fixture()
    assert title_el is not None
    assert title_el.get_text(strip=True) == "Head of Self-Serve Paid Media"


def test_company_selector_finds_company_name():
    _, company_el, _ = _parse_fixture()
    assert company_el is not None
    assert company_el.get_text(strip=True) == "Stripe"


def test_about_list_parses_job_type_and_category():
    _, _, about_texts = _parse_fixture()
    parsed = parse_about_list(about_texts)
    assert parsed["job_type"] == "Full-Time"
    assert parsed["category"] == "Full-Stack Programming"
    assert parsed["region"] == "Anywhere in the World"
