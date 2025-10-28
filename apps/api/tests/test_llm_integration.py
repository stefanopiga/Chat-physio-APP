"""
Test integrazione configurazione LLM (Story 2.12 P0).

Copre:
- 2.12-INT-002: Chat service istanzia ChatOpenAI con settings.openai_model
- 2.12-INT-004: Classifier usa settings.openai_model
- 2.12-INT-003: Override OPENAI_MODEL via env riflesso nei servizi
- 2.12-INT-005: Override OPENAI_TEMPERATURE_CLASSIFICATION funziona
"""
import sys
from unittest.mock import MagicMock, patch

import pytest

from api.config import Settings


def _override_settings(**overrides):
    """Crea Settings override per test DI."""
    defaults = {
        "supabase_url": "https://test.supabase.co",
        "supabase_service_role_key": "test-key",
        "supabase_jwt_secret": "test-secret",
        "openai_api_key": "test-openai-key",
    }
    defaults.update(overrides)
    return Settings.model_validate(defaults)


@pytest.mark.parametrize(
    ("model_override", "temp_override"),
    [
        ("gpt-4-nano", None),
        ("gpt-5-nano", 0.5),
    ],
)
def test_chat_service_uses_settings_model(model_override, temp_override):
    """
    2.12-INT-002: Chat service istanzia ChatOpenAI con model/temperature da Settings.
    """
    custom_settings = _override_settings(
        openai_model=model_override,
        openai_temperature_chat=temp_override,
    )

    # Rimuovo cache modulo PRIMA del patch per reload pulito
    if "api.services.chat_service" in sys.modules:
        del sys.modules["api.services.chat_service"]

    # Patch sorgente langchain_openai invece di import target
    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        from api.services.chat_service import get_llm

        result = get_llm(settings=custom_settings)

        assert result is mock_instance
        call_kwargs = mock_chat_openai.call_args.kwargs

        assert call_kwargs["model"] == model_override
        if temp_override is not None:
            assert call_kwargs["temperature"] == temp_override
        else:
            assert "temperature" not in call_kwargs


def test_chat_service_feature_flag_disabled():
    """
    Verifica fallback a gpt-5-nano quando llm_config_refactor_enabled=False.
    """
    custom_settings = _override_settings(
        openai_model="gpt-4o",
        llm_config_refactor_enabled=False,
    )

    if "api.services.chat_service" in sys.modules:
        del sys.modules["api.services.chat_service"]

    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        from api.services.chat_service import get_llm

        result = get_llm(settings=custom_settings)

        assert result is mock_instance
        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "gpt-5-nano"


def test_classifier_uses_settings_model():
    """
    2.12-INT-004: Classifier usa settings.openai_model e temperature_classification.
    """
    custom_settings = _override_settings(
        openai_model="gpt-4-nano",
        openai_temperature_classification=1.2,
    )

    if "api.knowledge_base.classifier" in sys.modules:
        del sys.modules["api.knowledge_base.classifier"]

    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        from api.knowledge_base.classifier import _get_llm

        result = _get_llm(settings=custom_settings)

        assert result is mock_instance
        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4-nano"
        assert call_kwargs["temperature"] == pytest.approx(1.2)


def test_classifier_feature_flag_disabled():
    """
    Verifica fallback classificatore quando feature flag disabilitato.
    """
    custom_settings = _override_settings(
        openai_model="gpt-4o",
        llm_config_refactor_enabled=False,
    )

    if "api.knowledge_base.classifier" in sys.modules:
        del sys.modules["api.knowledge_base.classifier"]

    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_instance = MagicMock()
        mock_chat_openai.return_value = mock_instance

        from api.knowledge_base.classifier import _get_llm

        result = _get_llm(settings=custom_settings)

        assert result is mock_instance
        call_kwargs = mock_chat_openai.call_args.kwargs
        assert call_kwargs["model"] == "gpt-5-nano"
        assert call_kwargs["temperature"] == 1


def test_env_override_openai_model(monkeypatch):
    """
    2.12-INT-003: Override OPENAI_MODEL via env riflesso in Settings.
    """
    from api import config as config_module

    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-override")

    config_module._settings = None
    settings = config_module.get_settings()
    config_module._settings = None

    assert settings.openai_model == "gpt-4o-override"


def test_env_override_temperature_classification(monkeypatch):
    """
    2.12-INT-005: Override OPENAI_TEMPERATURE_CLASSIFICATION via env.
    """
    from api import config as config_module

    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", "test-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_TEMPERATURE_CLASSIFICATION", "1.5")

    config_module._settings = None
    settings = config_module.get_settings()
    config_module._settings = None

    assert settings.openai_temperature_classification == pytest.approx(1.5)


def test_ag_endpoint_uses_settings_for_llm(monkeypatch):
    """
    2.12-E2E-001 (light): Endpoint /ag istanzia LLM con config centralizzata.
    
    Verifica che il router chat inietti Settings correttamente al chat service.
    
    Nota: Questo test è duplicato in test_chat.py con nome identico.
    Viene mantenuto qui per completezza P0 ma è già coperto.
    """
    pytest.skip("Test duplicato - già coperto in tests/routers/test_chat.py")

