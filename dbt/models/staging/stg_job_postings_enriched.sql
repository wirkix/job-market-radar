with source as (
    select * from {{ source('raw', 'job_postings_enriched') }}
)

select
    posting_id,
    is_data_role,
    coalesce(nullif(trim(seniority), ''), 'unknown')             as seniority,
    coalesce(nullif(trim(employment_type_norm), ''), 'Unknown')  as employment_type_norm,
    skills,
    summary,
    enrichment_model,
    enriched_at
from source
