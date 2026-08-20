-- Grain: one row per distinct company_name. Headquarters text isn't always
-- consistent across a company's postings (different postings phrase it
-- differently — see scraper/clean.py's extract_headquarters docstring), so
-- this takes any one non-null value per company rather than pretending
-- there's a single canonical source of truth for it.

with postings as (
    select * from {{ ref('stg_job_postings') }}
),

companies as (
    select
        company_name,
        max(company_headquarters) as company_headquarters
    from postings
    where company_name is not null
    group by company_name
)

select
    md5(lower(company_name)) as company_key,
    company_name,
    company_headquarters
from companies
