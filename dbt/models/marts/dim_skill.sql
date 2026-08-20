-- The LLM's casing isn't perfectly consistent across postings (e.g. "dbt"
-- on one posting, "DBT" on another) — both are real, observed variants.
-- Deduping on raw `skill` text before hashing would let both survive as
-- separate rows that then collide on the same md5(lower(...)) key, so this
-- groups by the key itself and picks one deterministic display string per
-- key, rather than deduping first and hashing second.

with skills as (
    select distinct skill
    from {{ ref('stg_job_skills') }}
),

keyed as (
    select
        md5(lower(skill)) as skill_key,
        skill
    from skills
)

select
    skill_key,
    min(skill) as skill
from keyed
group by skill_key
