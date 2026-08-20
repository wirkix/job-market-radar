-- One row per posting, lightly typed/renamed but not yet reshaped into the
-- star schema — that reshaping happens in marts/. Keyword-candidate
-- filtering does NOT happen here; every scraped posting stays visible in
-- staging, filtering to data roles is a marts-layer decision.

with source as (
    select * from {{ source('raw', 'job_postings_raw') }}
)

select
    posting_id,
    source                          as job_source,
    source_category,
    trim(job_title)                 as job_title,
    trim(company_name)              as company_name,
    nullif(trim(company_headquarters), '') as company_headquarters,
    nullif(trim(region), '')        as region,
    nullif(trim(job_type), '')      as job_type,
    nullif(trim(salary_text), '')   as salary_text,
    apply_before_text,
    description_text,
    apply_url,
    posted_at,
    posted_at::date                 as posted_date,
    is_data_role_keyword_match,
    first_scraped_at,
    last_scraped_at
from source
where posting_id is not null
