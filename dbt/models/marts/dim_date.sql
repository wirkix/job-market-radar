-- A generated date spine covering the full range of posting dates seen so
-- far — no dbt_utils dependency, just generate_series, to keep this
-- project's `dbt deps` step (and its dependency on the dbt package hub
-- being reachable) out of the picture entirely.

with bounds as (
    select
        min(posted_date) as min_date,
        max(posted_date) as max_date
    from {{ ref('stg_job_postings') }}
),

spine as (
    select generate_series(min_date, max_date, interval '1 day')::date as date_day
    from bounds
)

select
    to_char(date_day, 'YYYYMMDD')::int as date_key,
    date_day,
    extract(year from date_day)::int    as year,
    extract(month from date_day)::int   as month,
    extract(day from date_day)::int     as day,
    extract(isodow from date_day)::int  as iso_weekday,
    trim(to_char(date_day, 'Day'))      as day_name,
    trim(to_char(date_day, 'Month'))    as month_name,
    extract(isodow from date_day) in (6, 7) as is_weekend
from spine
