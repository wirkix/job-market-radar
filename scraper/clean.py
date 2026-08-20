"""Pure string/parsing helpers — no network, no DB. Kept separate from
discover.py / fetch_detail.py so they're trivial to unit test (see
tests/test_clean.py) without mocking HTTP calls.
"""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from scraper.config import DATA_ROLE_KEYWORDS

_WHITESPACE_RE = re.compile(r"\s+")

# Ordered so longer/more-specific labels are tried before their prefixes
# (e.g. "Apply before" before "Apply").
_ABOUT_LABELS = [
    "Posted on",
    "Apply before",
    "Job type",
    "Category",
    "Region",
    "Salary",
]


def normalize_whitespace(text: str | None) -> str | None:
    if text is None:
        return None
    collapsed = _WHITESPACE_RE.sub(" ", text).strip()
    return collapsed or None


def split_title(title_raw: str) -> tuple[str | None, str]:
    """WWR RSS titles are "Company: Job Title". Falls back gracefully for
    the rare listing that doesn't follow the pattern instead of raising.
    """
    if ":" in title_raw:
        company, _, job_title = title_raw.partition(":")
        return normalize_whitespace(company), normalize_whitespace(job_title) or title_raw.strip()
    return None, title_raw.strip()


def strip_html(html: str | None) -> str | None:
    if not html:
        return None
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return normalize_whitespace(text)


def posting_id_from_url(url: str) -> str:
    """The URL slug is WWR's own stable identifier for a listing — reused
    as our primary key so re-scraping the same posting is an upsert, not a
    duplicate.
    """
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def parse_pubdate(pubdate_raw: str | None) -> datetime | None:
    if not pubdate_raw:
        return None
    try:
        return parsedate_to_datetime(pubdate_raw)
    except (TypeError, ValueError):
        return None


def parse_about_list(item_texts: list[str]) -> dict[str, str | None]:
    """Each <li> in WWR's "About the job" sidebar is a label followed by a
    value with no separating punctuation ("Job type Full-Time"), so we
    strip the known label off the front of each item's flattened text.
    """
    result: dict[str, str | None] = {
        "posted_on_relative": None,
        "apply_before": None,
        "job_type": None,
        "category": None,
        "region": None,
        "salary": None,
    }
    key_by_label = {
        "Posted on": "posted_on_relative",
        "Apply before": "apply_before",
        "Job type": "job_type",
        "Category": "category",
        "Region": "region",
        "Salary": "salary",
    }
    for raw in item_texts:
        text = normalize_whitespace(raw)
        if not text:
            continue
        for label in _ABOUT_LABELS:
            if text.startswith(label):
                value = normalize_whitespace(text[len(label):])
                if value:
                    result[key_by_label[label]] = value
                break
    return result


def is_data_role_candidate(job_title: str | None, description_text: str | None) -> bool:
    haystack = f" {(job_title or '').lower()} {(description_text or '').lower()} "
    return any(keyword in haystack for keyword in DATA_ROLE_KEYWORDS)


_HEADQUARTERS_RE = re.compile(r"^headquarters:?\s*(.{1,200})$", re.IGNORECASE)
# Some postings run the company URL into the same line ("Minneapolis, MN
# URL: http://..."); trim it off rather than keeping it as part of the
# location string.
_TRAILING_URL_RE = re.compile(r"\s+(?:URL:|https?://).*$", re.IGNORECASE)


def extract_headquarters(description_html: str | None) -> str | None:
    """Best-effort only: WWR's detail page gates company info behind a
    signup wall, so this is scraped out of the free-text job description
    instead — and only some employers' postings follow a "Headquarters:
    ..." convention as their own first paragraph. None is a normal, common
    result here, not a bug; a real analytics consumer of this data should
    expect nulls.

    Matched against one block element's own text at a time (rather than the
    fully flattened description) so a "Headquarters: Berlin" first
    paragraph doesn't run on into the next, unrelated paragraph.
    """
    if not description_html:
        return None
    soup = BeautifulSoup(description_html, "html.parser")
    first_block = soup.find(["p", "li", "div"])
    if first_block is None:
        return None
    block_text = normalize_whitespace(first_block.get_text(" ", strip=True))
    if not block_text:
        return None
    match = _HEADQUARTERS_RE.match(block_text)
    if not match:
        return None
    value = _TRAILING_URL_RE.sub("", match.group(1))
    return normalize_whitespace(value)


def merge_posting(rss_item: dict, detail: dict | None) -> dict:
    """Combines the RSS discovery record (title, region, full description,
    pubDate) with the detail-page scrape (canonical company name, job type,
    salary, apply-before date) into one row shape ready for raw.job_postings_raw.
    """
    title_raw = rss_item["title_raw"]
    company_from_title, job_title = split_title(title_raw)
    description_html = rss_item.get("description_html")
    description_text = strip_html(description_html)

    about = (detail or {}).get("about", {})
    company_name = (detail or {}).get("company_name") or company_from_title

    return {
        "posting_id": rss_item["posting_id"],
        "source": rss_item["source"],
        "source_category": rss_item["source_category"],
        "title_raw": normalize_whitespace(title_raw),
        "job_title": (detail or {}).get("job_title") or job_title,
        "company_name": normalize_whitespace(company_name),
        "company_headquarters": extract_headquarters(description_html),
        "region": normalize_whitespace(about.get("region") or rss_item.get("region")),
        "category": normalize_whitespace(about.get("category") or rss_item.get("category")),
        "job_type": normalize_whitespace(about.get("job_type")),
        "salary_text": normalize_whitespace(about.get("salary")),
        "apply_before_text": normalize_whitespace(about.get("apply_before")),
        "description_html": description_html,
        "description_text": description_text,
        "apply_url": rss_item["apply_url"],
        "posted_at": parse_pubdate(rss_item.get("pubdate_raw")),
        "is_data_role_keyword_match": is_data_role_candidate(job_title, description_text),
    }
