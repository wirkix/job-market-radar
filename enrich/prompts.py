"""The one prompt this project sends to an LLM: turn a free-text job posting
into the structured fields the star schema needs (dim_skill, fact table's
seniority column, etc.) that no amount of regex/keyword matching gets
reliably out of prose.
"""

SYSTEM_PROMPT = """You are a data analyst who classifies remote job postings for a
labor-market dashboard. You are careful and literal: only report a skill,
seniority, or employment type that the posting text actually supports —
never guess or infer beyond what's written."""

# {job_title} / {company_name} / {description_text} are .format()-substituted
# in enrich_llm.py.
USER_PROMPT_TEMPLATE = """Classify this job posting using the record_job_analysis tool.

Job title: {job_title}
Company: {company_name}

Posting text:
{description_text}

Guidance:
- is_data_role: true only if the role is centrally about data engineering,
  analytics engineering, data science, ML engineering, data platform/infra,
  or business intelligence — not just a role that happens to mention "data"
  in passing (e.g. a general backend or product role is false).
- seniority: one of "junior", "mid", "senior", "lead", "unknown". Use
  "unknown" rather than guessing if the text gives no real signal.
- skills: concrete tools/languages/platforms actually named in the text
  (e.g. "Python", "dbt", "Snowflake", "Airflow", "Kafka", "AWS", "SQL",
  "Spark", "Kubernetes"). Normalize casing/spelling (e.g. "postgres" ->
  "PostgreSQL") but don't invent skills the text doesn't mention.
- summary: one plain sentence, under 30 words, in the tone of a labor-market
  report — not marketing copy from the posting itself.
"""

RECORD_JOB_ANALYSIS_TOOL = {
    "name": "record_job_analysis",
    "description": "Records the structured classification of one job posting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "is_data_role": {
                "type": "boolean",
                "description": "True if this is genuinely a data engineering/analytics/BI/ML role.",
            },
            "seniority": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "lead", "unknown"],
            },
            "employment_type_norm": {
                "type": "string",
                "description": "Normalized employment type, e.g. 'Full-Time', 'Contract', 'Part-Time', or 'Unknown'.",
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete tools/languages/platforms named in the posting, normalized casing.",
            },
            "summary": {
                "type": "string",
                "description": "One plain sentence (<30 words) summarizing the role for a labor-market report.",
            },
        },
        "required": ["is_data_role", "seniority", "employment_type_norm", "skills", "summary"],
    },
}
