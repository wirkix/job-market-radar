-- The many-to-many resolver between fact_job_posting and dim_skill: one row
-- per (posting, skill) pair, at the same grain as fact_job_posting's own
-- key on one side and dim_skill's key on the other.
--
-- Joins on the normalized md5(lower(...)) key rather than raw skill text —
-- dim_skill's `skill` column is a picked representative per key (see its
-- own model), so it won't textually equal every case variant that maps to
-- it. `distinct` guards the rare case where one posting's own skills list
-- contains more than one casing of the same tool (e.g. both "dbt" and
-- "DBT"), which would otherwise produce two identical bridge rows.

select distinct
    js.posting_id as job_posting_key,
    sk.skill_key
from {{ ref('stg_job_skills') }} js
inner join {{ ref('dim_skill') }} sk
    on sk.skill_key = md5(lower(js.skill))
