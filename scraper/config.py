"""Central config for the scraper: source, categories, filter keywords.

Everything here is deliberately data, not logic, so the "what are we
scraping and what counts as a data role" decisions live in one obvious
place instead of scattered across discover.py / clean.py.
"""

from __future__ import annotations

import os

SOURCE_NAME = "weworkremotely"
BASE_URL = "https://weworkremotely.com"

# WWR has no single "Data" category, so we pull from the categories where
# data engineering / analytics / BI roles actually get posted and filter
# down with DATA_ROLE_KEYWORDS below.
CATEGORIES: list[str] = [
    "remote-back-end-programming-jobs",
    "remote-devops-sysadmin-jobs",
    "remote-full-stack-programming-jobs",
    "all-other-remote-jobs",
]

# Pre-filter applied to (job_title + description_text) before a posting is
# considered a candidate data role. This is deliberately loose (recall over
# precision) — the LLM enrichment step (enrich/enrich_llm.py) makes the
# final, more precise call and this only decides what's worth spending an
# LLM call on.
DATA_ROLE_KEYWORDS: list[str] = [
    "data engineer",
    "data engineering",
    "analytics engineer",
    "data scientist",
    "data analyst",
    "business intelligence",
    "bi developer",
    "bi analyst",
    "data warehouse",
    "data platform",
    "etl",
    "elt",
    "machine learning engineer",
    "ml engineer",
    "mlops",
    " dbt ",
    "airflow",
    "snowflake",
    "databricks",
    "kafka",
    " sql ",
]

USER_AGENT = os.environ.get(
    "SCRAPER_USER_AGENT",
    "JobMarketRadarBot/1.0 (+https://github.com/wirkix/job-market-radar; "
    "portfolio project, respects robots.txt)",
)
CRAWL_DELAY_SECONDS = float(os.environ.get("SCRAPER_CRAWL_DELAY_SECONDS", "2"))
REQUEST_TIMEOUT_SECONDS = 20
