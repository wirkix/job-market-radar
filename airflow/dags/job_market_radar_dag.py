"""Daily pipeline: scrape WWR postings -> LLM-enrich the data-role
candidates -> rebuild the star-schema warehouse with dbt.

Each stage is its own task so a failure (e.g. WWR is briefly down, or the
LLM API is rate-limited) is visible and retryable per-stage in the Airflow
UI, rather than one opaque script failing partway through.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


def _run_scrape() -> None:
    from scraper.run import main as scrape_main

    scrape_main()


def _run_enrich() -> None:
    from enrich.enrich_llm import main as enrich_main

    enrich_main()


with DAG(
    dag_id="job_market_radar",
    description="Scrape WWR data-role postings, enrich with an LLM, model into a star-schema warehouse.",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    # Without this, unpausing (or a scheduler restart) can schedule the
    # latest missed interval *in addition* to any manual trigger, running
    # two copies of scrape_postings against WWR in parallel — exactly the
    # unserialized-crawl-delay situation this project is trying to avoid.
    max_active_runs=1,
    default_args={"retries": 1},
    tags=["job-market-radar", "portfolio"],
) as dag:
    scrape_postings = PythonOperator(
        task_id="scrape_postings",
        python_callable=_run_scrape,
    )

    enrich_postings = PythonOperator(
        task_id="enrich_postings",
        python_callable=_run_enrich,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        # dbt lives in its own venv, isolated from Airflow's own Python
        # environment (see docker/airflow.Dockerfile) — dbt-core and Airflow
        # pin conflicting dependency versions closely enough that installing
        # both into one environment sends pip's resolver into a death spiral.
        bash_command="cd /opt/airflow/project/dbt && /opt/airflow/dbt-venv/bin/dbt build --profiles-dir .",
    )

    scrape_postings >> enrich_postings >> dbt_build
