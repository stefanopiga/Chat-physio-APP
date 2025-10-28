"""
Tests per la configurazione LLM (Story 2.12 P0).

Copre:
- 2.12-UNIT-001: Validatore temperatura range + gestione None.
- Fallback sicuro per OPENAI_MODEL con valori mancanti.
"""
import pytest
from pydantic import ValidationError

from api.config import Settings


def _base_payload(**overrides):
    payload = {
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "service-key",
        "supabase_jwt_secret": "jwt-secret",
        "openai_api_key": "test-key",
    }
    payload.update(overrides)
    return payload


def test_temperature_chat_allows_none_and_str():
    """Valida Story 2.12-UNIT-001: None o stringhe numeriche sono accettate."""
    settings = Settings.model_validate(_base_payload(openai_temperature_chat=None))
    assert settings.openai_temperature_chat is None

    settings = Settings.model_validate(
        _base_payload(openai_temperature_chat=" 0.7 ")
    )
    assert settings.openai_temperature_chat == pytest.approx(0.7)


def test_temperature_chat_rejects_out_of_range():
    """Story 2.12-UNIT-001: temperatura > 2.0 genera errore."""
    with pytest.raises(ValueError):
        Settings.model_validate(
            _base_payload(openai_temperature_chat="2.5")
        )


def test_temperature_classification_defaults_and_validates():
    """Temperatura classificazione fallback 1.0 e valida range."""
    settings = Settings.model_validate(
        _base_payload(openai_temperature_classification="")
    )
    assert settings.openai_temperature_classification == pytest.approx(1.0)

    settings = Settings.model_validate(
        _base_payload(openai_temperature_classification="1.3")
    )
    assert settings.openai_temperature_classification == pytest.approx(1.3)

    with pytest.raises(ValueError):
        Settings.model_validate(
            _base_payload(openai_temperature_classification=-0.1)
        )


def test_openai_model_blank_fallback():
    """OPENAI_MODEL blank usa fallback gpt-5-nano."""
    settings = Settings.model_validate(_base_payload(openai_model="  "))
    assert settings.openai_model == "gpt-5-nano"


@pytest.mark.parametrize(
    ("overrides", "expected_field"),
    [
        ({"OPENAI_TEMPERATURE_CHAT": "bad-float"}, "openai_temperature_chat"),
        ({"OPENAI_TEMPERATURE_CLASSIFICATION": "bad"}, "openai_temperature_classification"),
    ],
)
def test_get_settings_safe_fail_for_invalid_env(monkeypatch, overrides, expected_field):
    """2.12-INT-007: boot applicazione fallisce in modo sicuro con env invalidi."""
    from api import config as config_module

    base_env = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "service-key",
        "SUPABASE_JWT_SECRET": "jwt-secret",
        "OPENAI_API_KEY": "test-key",
    }

    for key, value in base_env.items():
        monkeypatch.setenv(key, value)

    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    config_module._settings = None
    with pytest.raises(ValidationError) as exc:
        config_module.get_settings()
    config_module._settings = None
    assert expected_field in str(exc.value)
