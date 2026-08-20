"""Stage 1b of extraction: for each discovered posting, fetch its detail
page and scrape the metadata that isn't in the RSS feed — canonical job
title, company name, job type, category chip, region chip, salary chip,
and the apply-before date. (The free-text description itself is *not*
scraped from here — WWR gates it behind a signup wall on the detail page;
the RSS feed already gave us the full description, which is why discover.py
runs first.)
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from scraper.clean import parse_about_list
from scraper.config import REQUEST_TIMEOUT_SECONDS, USER_AGENT

_TITLE_SELECTOR = ".lis-container__header__hero__company-info__title"
_COMPANY_NAME_SELECTOR = ".lis-container__job__sidebar__companyDetails__info__title h3"
_ABOUT_ITEM_SELECTOR = ".lis-container__job__sidebar__job-about__list__item"


def fetch_job_detail(url: str) -> dict | None:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    if resp.status_code == 404:
        # Listings get taken down; a 404 here is a normal outcome, not an error.
        return None
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    title_el = soup.select_one(_TITLE_SELECTOR)
    company_el = soup.select_one(_COMPANY_NAME_SELECTOR)
    about_item_texts = [li.get_text(" ", strip=True) for li in soup.select(_ABOUT_ITEM_SELECTOR)]

    return {
        "job_title": title_el.get_text(" ", strip=True) if title_el else None,
        "company_name": company_el.get_text(" ", strip=True) if company_el else None,
        "about": parse_about_list(about_item_texts),
    }
