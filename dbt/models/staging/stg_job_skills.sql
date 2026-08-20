-- Unnests the enriched postings' skills array into one row per
-- (posting_id, skill) — the long/tidy shape marts/bridge_job_skill.sql and
-- marts/dim_skill.sql are built from.

with enriched as (
    select * from {{ ref('stg_job_postings_enriched') }}
),

unnested as (
    select
        posting_id,
        trim(skill) as skill
    from enriched,
    unnest(skills) as skill
)

select distinct
    posting_id,
    skill
from unnested
where skill is not null and skill != ''
