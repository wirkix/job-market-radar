import pytest

from enrich import providers


def test_build_user_prompt_includes_fields_and_truncates():
    long_description = "x" * 10_000
    prompt = providers._build_user_prompt("Data Engineer", "Acme", long_description)
    assert "Data Engineer" in prompt
    assert "Acme" in prompt
    assert len(prompt) < len(long_description)  # confirms truncation actually happened


def test_build_user_prompt_handles_missing_fields():
    prompt = providers._build_user_prompt("Data Engineer", None, None)
    assert "Unknown" in prompt
    assert "no description text scraped" in prompt


def test_classify_dispatches_to_anthropic(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "anthropic")
    called = {}

    def fake_anthropic(job_title, company_name, description_text):
        called["args"] = (job_title, company_name, description_text)
        return {"is_data_role": True}

    monkeypatch.setattr(providers, "classify_with_anthropic", fake_anthropic)
    result = providers.classify("Data Engineer", "Acme", "some text")

    assert result == {"is_data_role": True}
    assert called["args"] == ("Data Engineer", "Acme", "some text")


def test_classify_dispatches_to_ollama(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "ollama")
    monkeypatch.setattr(providers, "classify_with_ollama", lambda *a: {"is_data_role": False})

    result = providers.classify("Marketing Manager", "Acme", "some text")
    assert result == {"is_data_role": False}


def test_classify_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "made-up-provider")
    with pytest.raises(ValueError, match="Unknown ENRICHMENT_PROVIDER"):
        providers.classify("Data Engineer", "Acme", "some text")


def test_unwrap_if_schema_shaped_passes_through_flat_dict():
    flat = {"is_data_role": True, "seniority": "senior"}
    assert providers._unwrap_if_schema_shaped(flat) == flat


def test_unwrap_if_schema_shaped_unwraps_nested_properties():
    # This is the exact failure mode observed from llama3.2:3b: it echoed
    # the JSON Schema shape back with real values nested under "properties"
    # instead of producing a flat object.
    nested = {
        "type": "object",
        "properties": {
            "is_data_role": True,
            "seniority": "senior",
            "skills": ["Python", "dbt"],
        },
    }
    assert providers._unwrap_if_schema_shaped(nested) == {
        "is_data_role": True,
        "seniority": "senior",
        "skills": ["Python", "dbt"],
    }


def test_current_model_name_defaults(monkeypatch):
    monkeypatch.setenv("ENRICHMENT_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    assert providers.current_model_name() == "claude-haiku-4-5-20251001"

    monkeypatch.setenv("ENRICHMENT_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1")
    assert providers.current_model_name() == "llama3.1"
