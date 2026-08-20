"""Two interchangeable LLM backends for the same classification task —
Anthropic's API (tool-use, for a guaranteed-schema response) or a local
Ollama model (JSON mode, best-effort schema). Picked by ENRICHMENT_PROVIDER
so this project can run for $0 against a local model, or against Claude for
better extraction quality, without touching the rest of the pipeline.
"""

from __future__ import annotations

import json
import os

import requests

from enrich.prompts import RECORD_JOB_ANALYSIS_TOOL, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Long postings get truncated before hitting the LLM — bounds token cost and
# most postings say everything relevant to classification in the first
# couple thousand characters anyway (role summary, then boilerplate).
_MAX_DESCRIPTION_CHARS = 6000


def _build_user_prompt(job_title: str, company_name: str | None, description_text: str | None) -> str:
    text = (description_text or "")[:_MAX_DESCRIPTION_CHARS]
    return USER_PROMPT_TEMPLATE.format(
        job_title=job_title or "Unknown",
        company_name=company_name or "Unknown",
        description_text=text or "(no description text scraped)",
    )


def classify_with_anthropic(job_title: str, company_name: str | None, description_text: str | None) -> dict:
    import anthropic  # imported lazily so this provider is optional at runtime

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        tools=[RECORD_JOB_ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "record_job_analysis"},
        messages=[{"role": "user", "content": _build_user_prompt(job_title, company_name, description_text)}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_job_analysis":
            return block.input
    raise RuntimeError(f"Claude response had no record_job_analysis tool_use block: {response.content!r}")


# Shown to the model as a filled-in example rather than the raw JSON Schema
# — smaller local models (tested against llama3.2:3b) tend to echo a literal
# schema dump back verbatim (nesting the real values inside a "properties"
# key) instead of producing the flat object the schema describes.
_OLLAMA_EXAMPLE_SHAPE = {
    "is_data_role": True,
    "seniority": "senior",
    "employment_type_norm": "Full-Time",
    "skills": ["Python", "dbt", "Snowflake"],
    "summary": "One plain sentence describing the role.",
}


def classify_with_ollama(job_title: str, company_name: str | None, description_text: str | None) -> dict:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")

    prompt = (
        SYSTEM_PROMPT
        + "\n\n"
        + _build_user_prompt(job_title, company_name, description_text)
        + "\n\nRespond with ONLY a single flat JSON object with exactly these five keys "
        + "(no nesting, no nulls, no markdown fences, no extra keys), following this shape:\n"
        + json.dumps(_OLLAMA_EXAMPLE_SHAPE)
        + '\n\nseniority must be one of: "junior", "mid", "senior", "lead", "unknown".'
    )
    resp = requests.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "format": "json", "stream": False},
        timeout=180,
    )
    resp.raise_for_status()
    data = json.loads(resp.json()["response"])
    return _unwrap_if_schema_shaped(data)


def _unwrap_if_schema_shaped(data: dict) -> dict:
    """Defensive net for exactly the failure mode above, in case a
    different local model does it anyway: if the model nested the real
    answer inside a JSON-Schema-shaped envelope, pull it back out.
    """
    if "is_data_role" not in data and isinstance(data.get("properties"), dict):
        return data["properties"]
    return data


def classify(job_title: str, company_name: str | None, description_text: str | None) -> dict:
    provider = os.environ.get("ENRICHMENT_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return classify_with_anthropic(job_title, company_name, description_text)
    if provider == "ollama":
        return classify_with_ollama(job_title, company_name, description_text)
    raise ValueError(f"Unknown ENRICHMENT_PROVIDER: {provider!r} (expected 'anthropic' or 'ollama')")


def current_model_name() -> str:
    provider = os.environ.get("ENRICHMENT_PROVIDER", "anthropic").lower()
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    return os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
