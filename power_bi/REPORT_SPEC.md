# Power BI report spec

The pipeline (scrape → enrich → dbt) is fully automated; this last step —
authoring the actual `.pbix` report — isn't, because Power BI Desktop is a
GUI app with no CLI/API for building reports from code. This doc is the
spec to build it from in ~20-30 minutes, so the manual part is fast and
repeatable rather than improvised.

## Connect

Power BI Desktop → Get Data → PostgreSQL database.

- Server: `localhost:5432` (or wherever the `postgres` container is exposed)
- Database: `job_market_radar`
- Import the five `marts.*` tables: `fact_job_posting`, `dim_company`,
  `dim_location`, `dim_date`, `dim_skill`, `bridge_job_skill`.

## Model

Power BI should auto-detect most of these from the FK-shaped column names,
but set explicitly if it doesn't:

| From | To | Cardinality |
|---|---|---|
| `fact_job_posting[date_key]` | `dim_date[date_key]` | many-to-one |
| `fact_job_posting[company_key]` | `dim_company[company_key]` | many-to-one |
| `fact_job_posting[location_key]` | `dim_location[location_key]` | many-to-one |
| `fact_job_posting[job_posting_key]` | `bridge_job_skill[job_posting_key]` | one-to-many |
| `bridge_job_skill[skill_key]` | `dim_skill[skill_key]` | many-to-one |

Mark `dim_date` as a Date Table (Modeling → Mark as Date Table →
`dim_date[date_day]`).

## Measures (DAX)

```dax
Total Postings = COUNTROWS(fact_job_posting)

Confirmed Data Roles =
CALCULATE([Total Postings], fact_job_posting[is_data_role] = TRUE)

Enrichment Coverage =
DIVIDE(
    CALCULATE([Total Postings], fact_job_posting[is_enriched] = TRUE),
    [Total Postings]
)

Postings This Week =
CALCULATE(
    [Total Postings],
    DATESINPERIOD(dim_date[date_day], MAX(dim_date[date_day]), -7, DAY)
)
```

## Pages

**1. Overview**
- KPI cards: Total Postings, Confirmed Data Roles, Enrichment Coverage
- Line chart: Postings by `dim_date[date_day]` (weekly trend)
- Donut: postings by `fact_job_posting[seniority]`

**2. Skills demand**
- Horizontal bar: `[Total Postings]` by `dim_skill[skill]`, top 20, filtered
  to `is_data_role = TRUE`
- Matrix: `dim_skill[skill]` × `fact_job_posting[seniority]`, values =
  `[Total Postings]` — shows which tools skew junior vs. senior

**3. Companies & postings**
- Table: `dim_company[company_name]`, `fact_job_posting[job_title]`,
  `[seniority]`, `[salary_text]`, `[apply_url]` (set as a web URL column so
  it's clickable)
- Slicers: `dim_location[region]`, `fact_job_posting[job_type]`

## Publish

File → Publish → Power BI service (free tier), then **File → Embed report
→ Publish to web** on the published report for a public, no-login embed
URL — that's the link that goes in `portfolio/page.tsx`'s `demo` field.
Publish to web makes the report fully public; don't use it if the data
ever includes anything sensitive (it won't here — this only contains
already-public job listing text).
