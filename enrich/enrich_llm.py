"""Stage 2 of the pipeline: process & enrich. Takes every keyword-flagged
candidate from raw.job_postings_raw that hasn't been enriched yet, asks an
LLM to turn it into structured fields, and writes the result to
raw.job_postings_enriched — which dbt's marts then join against.
"""

from __future__ import annotations

from dotenv import load_dotenv

from enrich.providers import classify, current_model_name
from scraper.db import ensure_schema, get_connection

_SELECT_CANDIDATES = """
    SELECT r.posting_id, r.job_title, r.company_name, r.description_text
    FROM raw.job_postings_raw r
    LEFT JOIN raw.job_postings_enriched e USING (posting_id)
    WHERE r.is_data_role_keyword_match = true
      AND e.posting_id IS NULL
    ORDER BY r.posted_at DESC NULLS LAST;
"""

_UPSERT_ENRICHMENT = """
    INSERT INTO raw.job_postings_enriched (
        posting_id, is_data_role, seniority, employment_type_norm, skills, summary, enrichment_model
    ) VALUES (
        %(posting_id)s, %(is_data_role)s, %(seniority)s, %(employment_type_norm)s,
        %(skills)s, %(summary)s, %(enrichment_model)s
    )
    ON CONFLICT (posting_id) DO UPDATE SET
        is_data_role          = EXCLUDED.is_data_role,
        seniority              = EXCLUDED.seniority,
        employment_type_norm  = EXCLUDED.employment_type_norm,
        skills                = EXCLUDED.skills,
        summary                = EXCLUDED.summary,
        enrichment_model      = EXCLUDED.enrichment_model,
        enriched_at            = now();
"""


def get_candidates(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(_SELECT_CANDIDATES)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def upsert_enrichment(conn, posting_id: str, result: dict, model_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            _UPSERT_ENRICHMENT,
            {
                "posting_id": posting_id,
                "is_data_role": result.get("is_data_role"),
                "seniority": result.get("seniority", "unknown"),
                "employment_type_norm": result.get("employment_type_norm"),
                "skills": result.get("skills") or [],
                "summary": result.get("summary"),
                "enrichment_model": model_name,
            },
        )


def main() -> None:
    load_dotenv()

    conn = get_connection()
    ensure_schema(conn)
    candidates = get_candidates(conn)
    print(f"{len(candidates)} candidate postings need enrichment.")

    model_name = current_model_name()
    succeeded, failed = 0, 0
    for row in candidates:
        try:
            result = classify(row["job_title"], row["company_name"], row["description_text"])
            upsert_enrichment(conn, row["posting_id"], result, model_name)
            conn.commit()
            succeeded += 1
        except Exception as exc:  # noqa: BLE001 — one bad posting shouldn't kill the run
            print(f"  enrichment failed for {row['posting_id']}: {exc}")
            conn.rollback()
            failed += 1

    print(f"Enriched {succeeded} postings via {model_name} ({failed} failed).")
    conn.close()


if __name__ == "__main__":
    main()
