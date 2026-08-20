"""Stage 1 of extraction: discover candidate postings via WWR's per-category
RSS feeds (see /categories/<slug> — it's actually RSS, not HTML; confirmed
by fetching it directly. robots.txt for weworkremotely.com allows
`User-agent: *` on everything except account/admin paths, so this is within
the terms the site itself publishes).
"""

from __future__ import annotations

import time
from xml.etree import ElementTree

import requests

from scraper.clean import posting_id_from_url
from scraper.config import (
    BASE_URL,
    CRAWL_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    SOURCE_NAME,
    USER_AGENT,
)


def fetch_category_feed(category: str) -> list[dict]:
    # The bare /categories/<slug> URL serves WWR's JS-rendered app shell, not
    # data — the .rss suffix is what actually returns the category's feed.
    url = f"{BASE_URL}/categories/{category}.rss"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    resp.raise_for_status()
    root = ElementTree.fromstring(resp.content)

    items = []
    for item_el in root.findall("./channel/item"):
        link = (item_el.findtext("link") or "").strip()
        if not link:
            continue
        items.append(
            {
                "source": SOURCE_NAME,
                "source_category": category,
                "title_raw": item_el.findtext("title") or "",
                "region": item_el.findtext("region"),
                "category": item_el.findtext("category"),
                "description_html": item_el.findtext("description"),
                "pubdate_raw": item_el.findtext("pubDate"),
                "apply_url": link,
                "posting_id": posting_id_from_url(link),
            }
        )
    return items


def discover_all(categories: list[str]) -> dict[str, dict]:
    """One pass over every configured category feed, deduped by posting_id
    (the same listing can legitimately appear in more than one category).
    A Crawl-delay is honored between requests, per robots.txt.
    """
    by_id: dict[str, dict] = {}
    for i, category in enumerate(categories):
        for item in fetch_category_feed(category):
            by_id.setdefault(item["posting_id"], item)
        if i < len(categories) - 1:
            time.sleep(CRAWL_DELAY_SECONDS)
    return by_id
