import logging


from api.config import Settings
from api.knowledge_base import classifier


def _base_settings_data(**overrides) -> dict:
    data = {
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "service-key",
        "supabase_jwt_secret": "jwt-secret",
        "openai_api_key": "sk-test",
    }
    data.update(overrides)
    return data


def test_get_llm_passes_settings_parameters(monkeypatch, caplog):
    captured_kwargs = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(classifier, "ChatOpenAI", DummyLLM)
    caplog.set_level(logging.INFO, logger="api")

    settings = Settings.model_validate(
        _base_settings_data(
            openai_base_url="https://openai.test/v1",
            openai_project="diag-project",
            openai_model="gpt-4o-mini",
            openai_temperature_classification=0.5,
        )
    )

    classifier._get_llm(settings)

    assert captured_kwargs["api_key"] == "sk-test"
    assert captured_kwargs["base_url"] == "https://openai.test/v1"
    # Story 6.2 Fix: project not passed to avoid API compatibility issues
    assert "project" not in captured_kwargs
    assert captured_kwargs["model"] == "gpt-4o-mini"
    assert captured_kwargs["temperature"] == 0.5
    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "classifier_llm_initialized"
        and record.msg.get("base_url") == "https://openai.test/v1"
        # project not in log - see classifier.py comment
        for record in caplog.records
    )


def test_get_llm_feature_flag_fallback_preserves_base_settings(monkeypatch):
    captured_kwargs = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

    monkeypatch.setattr(classifier, "ChatOpenAI", DummyLLM)

    settings = Settings.model_validate(
        _base_settings_data(
            llm_config_refactor_enabled=False,
            openai_base_url="https://fallback.test/v1",
            openai_project="fallback-project",
        )
    )

    classifier._get_llm(settings)

    assert captured_kwargs["api_key"] == "sk-test"
    assert captured_kwargs["base_url"] == "https://fallback.test/v1"
    # Story 6.2 Fix: project not passed
    assert "project" not in captured_kwargs
    assert captured_kwargs["model"] == "gpt-5-nano"
    assert captured_kwargs["temperature"] == 1

