# Job Market Radar

Scrapes remote data-engineering/analytics job postings, uses an LLM to pull
structured skills/seniority out of the free-text descriptions, and models
the result into a classic star-schema warehouse — to answer one question:
**what do employers actually ask for in data roles right now?**

Built as a portfolio piece to demonstrate a full data engineering pipeline
end to end: extraction & cleansing → processing & enrichment →
visualization — each stage a real, separately-runnable piece, not a single
monolithic script.

## Architecture

```
 WWR category RSS feeds            WWR job detail pages
 (discovery: title, region,        (job type, salary, apply-by,
  full description)                 canonical company name)
         │                                  │
         └──────────────┬───────────────────┘
                         ▼
                 scraper/ (Python)
              extract + clean + merge
                         │
                         ▼
          Postgres: raw.job_postings_raw
                         │
                         ▼
              enrich/ (Claude API or Ollama)
        classify: is_data_role, seniority,
             skills[], employment type
                         │
                         ▼
        Postgres: raw.job_postings_enriched
                         │
                         ▼
                    dbt (staging → marts)
                         │
                         ▼
     ┌────────────────────────────────────────┐
     │  fact_job_posting                       │
     │  dim_company · dim_location · dim_date  │
     │  dim_skill · bridge_job_skill           │
     └────────────────────────────────────────┘
                         │
                         ▼
                     Power BI
        (see power_bi/REPORT_SPEC.md — the one
         manual step; Power BI has no authoring API)
```

All three data stages (scrape, enrich, dbt build) are orchestrated daily by
one Airflow DAG: [`airflow/dags/job_market_radar_dag.py`](airflow/dags/job_market_radar_dag.py).

## Why WeWorkRemotely

No job board has a clean, uniformly-licensed "scrape me" dataset for this,
so the choice came down to what's actually compliant. WWR's `robots.txt`
allows `User-agent: *` on everything except account/admin paths, with no
special carve-out disallowing generic scrapers — unlike some other boards
that explicitly disallow AI/scraping bots by name in robots.txt while
technically leaving a loophole for an unnamed user agent. The scraper
identifies itself with a descriptive User-Agent (see `.env.example`) and
honors a crawl delay between requests.

Category pages (`/categories/<slug>`) serve a JS app shell; the actual data
comes from `/categories/<slug>.rss` — an RSS feed with the full job
description. The detail pages (`/remote-jobs/<slug>`) are scraped
separately for fields the RSS doesn't carry (job type, salary, apply-by
date, canonical company name) — WWR gates the *description* body on the
detail page behind a signup wall, but that metadata is public.

## Setup

**Requires:** Docker Desktop, and either an Anthropic API key or a local
Ollama install (see `.env`'s `ENRICHMENT_PROVIDER`).

```bash
cp .env.example .env
# edit .env: set POSTGRES_PASSWORD, AIRFLOW_ADMIN_PASSWORD, and either
# ANTHROPIC_API_KEY (ENRICHMENT_PROVIDER=anthropic) or leave the Ollama
# defaults (ENRICHMENT_PROVIDER=ollama, OLLAMA_HOST reachable from Docker)

# Optional but recommended — a real Fernet key instead of Airflow
# generating a throwaway one on every restart:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste the output into AIRFLOW__CORE__FERNET_KEY in .env

docker compose up -d --build
```

Airflow UI: http://localhost:8080 (login from `AIRFLOW_ADMIN_USER` /
`AIRFLOW_ADMIN_PASSWORD` in `.env`). Unpause the `job_market_radar` DAG and
trigger it, or wait for the daily schedule.

Postgres is reachable at `localhost:5432` (`POSTGRES_DB` /
`POSTGRES_USER` / `POSTGRES_PASSWORD` from `.env`) for Power BI or any
other client to connect to directly.

## Running pieces individually (without Airflow)

Useful for development/debugging — each stage is a plain Python entrypoint:

```bash
python -m venv .venv && .venv\Scripts\activate  # Windows
pip install -r requirements-dev.txt

# needs POSTGRES_* env vars pointing at a reachable Postgres (e.g. the
# docker-compose one, with its port published to localhost)
python -m scraper.run
python -m enrich.enrich_llm
```

`dbt build` needs the `dbt-postgres` adapter, listed in
`requirements-dbt.txt` and installed into its own isolated venv inside the
Airflow containers (`docker/airflow.Dockerfile`) — dbt-core and
apache-airflow pin conflicting dependency versions closely enough that
installing both into one Python environment sends pip's resolver into a
multi-hour death spiral (`ResolutionTooDeep`) instead of a real conflict
error. If you want to run dbt from the host, install
`requirements-dbt.txt` into its own venv there too rather than alongside
`requirements-dev.txt`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/
```

Pure logic (string cleaning, title splitting, keyword matching) and a
fixture-based test against a real saved WWR detail page — the latter is
there specifically so a WWR site redesign breaks a test loudly instead of
the scraper silently returning nulls forever in production.

## Data model

Star schema, one fact table:

- **`fact_job_posting`** — grain: one row per posting that matched the
  data-role keyword pre-filter (see `scraper/config.py`). Carries the LLM's
  `is_data_role`/`seniority`/`employment_type_norm` verdict, nullable until
  enrichment has run.
- **`dim_company`**, **`dim_location`**, **`dim_date`** — standard
  conformed dimensions.
- **`dim_skill`** + **`bridge_job_skill`** — the skills array from
  enrichment, resolved to a proper many-to-many bridge rather than left as
  an array column, so "top skills this month" is a normal `GROUP BY`.

## Known limitations

- **Company headquarters** is best-effort, scraped out of free-text
  ("Headquarters: ..." as a posting's own first paragraph) because WWR's
  detail page gates that field behind a signup wall. Frequently null — see
  `scraper/clean.py::extract_headquarters`.
- **Keyword pre-filter has real recall gaps** (`scraper/config.py`) — a
  posting titled e.g. "Senior Software Engineer, Data Layer" without
  further data-specific language in the body can slip past it. This is a
  deliberate cost/recall tradeoff (only keyword-flagged postings get sent
  to the LLM), documented rather than hidden.
- **Power BI is a manual step** — see `power_bi/REPORT_SPEC.md`.
