"""CLI / Airflow entrypoint for the extract-and-clean stage.

Runs the whole scraper in one call: discover postings across all configured
categories, fetch the detail page only for postings we haven't seen before
(re-fetching detail on every run would be both slow and pointless — job
type/salary/company essentially never change after posting), merge each
posting into one clean row, and upsert into raw.job_postings_raw.
"""

from __future__ import annotations

import time

from dotenv import load_dotenv

from scraper.clean import merge_posting
from scraper.config import CATEGORIES, CRAWL_DELAY_SECONDS
from scraper.db import ensure_schema, get_connection, upsert_postings
from scraper.discover import discover_all
from scraper.fetch_detail import fetch_job_detail


def get_existing_ids(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT posting_id FROM raw.job_postings_raw")
        return {row[0] for row in cur.fetchall()}


def main() -> None:
    load_dotenv()  # no-op inside Airflow, where env vars are already set

    conn = get_connection()
    ensure_schema(conn)
    existing_ids = get_existing_ids(conn)

    discovered = discover_all(CATEGORIES)
    print(f"Discovered {len(discovered)} unique postings across {len(CATEGORIES)} categories.")

    new_ids = {pid for pid in discovered if pid not in existing_ids}
    print(f"{len(new_ids)} are new — fetching their detail pages (skipping the rest).")

    merged = []
    for posting_id, rss_item in discovered.items():
        detail = None
        if posting_id in new_ids:
            try:
                detail = fetch_job_detail(rss_item["apply_url"])
            except Exception as exc:  # noqa: BLE001 — one bad page shouldn't kill the run
                print(f"  detail fetch failed for {posting_id}: {exc}")
            time.sleep(CRAWL_DELAY_SECONDS)
        merged.append(merge_posting(rss_item, detail))

    count = upsert_postings(conn, merged)
    candidates = sum(1 for p in merged if p["is_data_role_keyword_match"])
    print(f"Upserted {count} postings ({candidates} flagged as data-role candidates for LLM enrichment).")
    conn.close()


if __name__ == "__main__":
    main()
