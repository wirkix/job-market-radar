-- Grain: one row per job posting that passed the keyword pre-filter (see
-- scraper/config.py DATA_ROLE_KEYWORDS) — this warehouse only tracks data
-- roles, not the whole job board, so non-candidates never make it into the
-- fact table at all. `is_data_role` (from the LLM) is nullable: null means
-- "not enriched yet", not "confirmed not a data role" — that distinction
-- matters if you're filtering for confirmed-only rows downstream.

with postings as (
    select * from {{ ref('stg_job_postings') }}
    where is_data_role_keyword_match = true
),

enriched as (
    select * from {{ ref('stg_job_postings_enriched') }}
),

company as (
    select * from {{ ref('dim_company') }}
),

location as (
    select * from {{ ref('dim_location') }}
),

date_dim as (
    select * from {{ ref('dim_date') }}
)

select
    p.posting_id                              as job_posting_key,
    d.date_key,
    c.company_key,
    l.location_key,

    p.job_source,
    p.source_category,
    p.job_title,
    p.job_type,
    p.salary_text,
    p.apply_before_text,
    p.apply_url,
    p.posted_at,
    p.posted_date,

    e.is_data_role,
    coalesce(e.seniority, 'unknown')            as seniority,
    coalesce(e.employment_type_norm, 'Unknown')  as employment_type_norm,
    e.summary,
    e.enrichment_model,
    (e.posting_id is not null)                  as is_enriched

from postings p
left join enriched e
    on e.posting_id = p.posting_id
left join company c
    on c.company_name = p.company_name
left join location l
    on l.region = coalesce(p.region, 'Unspecified')
left join date_dim d
    on d.date_day = p.posted_date
