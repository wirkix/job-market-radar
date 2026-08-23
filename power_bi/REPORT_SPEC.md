# Power BI report spec

The pipeline (scrape → enrich → dbt) is fully automated; this last step —
authoring the actual `.pbix` report — isn't, because Power BI Desktop is a
GUI app with no CLI/API for building reports from code. This doc is the
spec to build it from in ~20-30 minutes, so the manual part is fast and
repeatable rather than improvised.

## Connect

Power BI Desktop → Get Data → PostgreSQL database.

- Server: `localhost:5433` (the `postgres` container's host-side port —
  remapped off the default 5432 because this dev machine also runs a
  native PostgreSQL 15 Windows service that occupies 5432; see
  `docker-compose.yml`'s `postgres.ports` comment)
- Database: `job_market_radar`
- Import the six `public_marts.*` tables: `fact_job_posting`,
  `dim_company`, `dim_location`, `dim_date`, `dim_skill`,
  `bridge_job_skill`.

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
- Horizontal bar: `[Total Postings]` by `dim_company[company_name]`, sorted
  descending, Top N filter (visual-level filter on `[Total Postings]`) to
  keep it to the top ~17 employers
- Table: `fact_job_posting[job_title]`, `[apply_url]` (set as a web URL
  column so it's clickable) — click a bar in the chart to cross-filter the
  table down to that company's actual listings. `company_name` is dropped
  from the table since the chart selection already identifies it;
  `seniority`/`salary_text` are dropped as mostly-uniform/mostly-null and
  add no signal here. No slicers — the report isn't being published
  interactively (see Publish below), so click-to-filter via the chart is
  the only filtering surface that matters.

## Publish

Not published to the Power BI service / embedded via Publish to web. The
portfolio page instead links to two static artifacts: the `.pbix` file
itself (download, for anyone who wants to open it in their own Power BI
Desktop) and a PDF export of the report (`File → Export → Export to PDF`)
as a no-login static preview. Both live in this `power_bi/` directory
(`job_market_radar.pbix`, `job_market_radar.pdf`) and get re-exported
whenever the report changes — the PDF is what `portfolio/page.tsx` should
link/embed as the static preview, the `.pbix` as the download.
