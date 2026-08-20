-- Grain: one row per distinct job region (where the role is open to remote
-- workers from — e.g. "Anywhere in the World", "US Only"). Deliberately
-- separate from the company's own headquarters, which lives on dim_company
-- instead: those are two different real-world concepts that happened to
-- both show up as "location-ish" text during scraping.

with postings as (
    select * from {{ ref('stg_job_postings') }}
),

locations as (
    select distinct coalesce(region, 'Unspecified') as region
    from postings
)

select
    md5(lower(region)) as location_key,
    region
from locations
