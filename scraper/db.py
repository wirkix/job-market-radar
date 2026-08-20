"""Connection + idempotent DDL + upsert for the `raw` schema. This is the
only module in the project that talks to Postgres directly on the write
side (dbt owns everything downstream of `raw`).
"""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.job_postings_raw (
    posting_id                  TEXT PRIMARY KEY,
    source                      TEXT NOT NULL,
    source_category             TEXT,
    title_raw                   TEXT,
    job_title                   TEXT,
    company_name                TEXT,
    company_headquarters        TEXT,
    region                      TEXT,
    category                    TEXT,
    job_type                    TEXT,
    salary_text                 TEXT,
    apply_before_text           TEXT,
    description_html            TEXT,
    description_text            TEXT,
    apply_url                   TEXT NOT NULL,
    posted_at                   TIMESTAMPTZ,
    is_data_role_keyword_match  BOOLEAN NOT NULL DEFAULT FALSE,
    first_scraped_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_scraped_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.job_postings_enriched (
    posting_id            TEXT PRIMARY KEY REFERENCES raw.job_postings_raw(posting_id),
    is_data_role          BOOLEAN,
    seniority              TEXT,
    employment_type_norm  TEXT,
    skills                TEXT[],
    summary                TEXT,
    enrichment_model      TEXT,
    enriched_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_UPSERT_POSTING = """
INSERT INTO raw.job_postings_raw (
    posting_id, source, source_category, title_raw, job_title, company_name,
    company_headquarters, region, category, job_type, salary_text,
    apply_before_text, description_html, description_text, apply_url,
    posted_at, is_data_role_keyword_match
) VALUES (
    %(posting_id)s, %(source)s, %(source_category)s, %(title_raw)s, %(job_title)s,
    %(company_name)s, %(company_headquarters)s, %(region)s, %(category)s,
    %(job_type)s, %(salary_text)s, %(apply_before_text)s, %(description_html)s,
    %(description_text)s, %(apply_url)s, %(posted_at)s, %(is_data_role_keyword_match)s
)
ON CONFLICT (posting_id) DO UPDATE SET
    source_category            = EXCLUDED.source_category,
    title_raw                  = EXCLUDED.title_raw,
    job_title                  = EXCLUDED.job_title,
    company_name                = EXCLUDED.company_name,
    company_headquarters        = EXCLUDED.company_headquarters,
    region                      = EXCLUDED.region,
    category                    = EXCLUDED.category,
    job_type                    = EXCLUDED.job_type,
    salary_text                = EXCLUDED.salary_text,
    apply_before_text          = EXCLUDED.apply_before_text,
    description_html            = EXCLUDED.description_html,
    description_text            = EXCLUDED.description_text,
    apply_url                  = EXCLUDED.apply_url,
    posted_at                  = EXCLUDED.posted_at,
    is_data_role_keyword_match  = EXCLUDED.is_data_role_keyword_match,
    last_scraped_at            = now();
"""


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "job_market_radar"),
        user=os.environ.get("POSTGRES_USER", "radar"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
    )


def ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(_DDL)
    conn.commit()


def upsert_postings(conn, postings: list[dict]) -> int:
    if not postings:
        return 0
    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, _UPSERT_POSTING, postings)
    conn.commit()
    return len(postings)
