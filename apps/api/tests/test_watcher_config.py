import logging
import os
import json

import pytest

from api.config import Settings
from api.debug import print_settings
from api.ingestion.config import IngestionConfig


def _base_settings_data(**overrides) -> dict:
    data = {
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "service-key",
        "supabase_jwt_secret": "jwt-secret",
        "openai_api_key": "sk-test",
    }
    data.update(overrides)
    return data


def test_process_env_override_logs_warning(monkeypatch, caplog):
    monkeypatch.setenv("OPENAI_API_KEY", "override-process")
    settings = Settings.model_validate(
        _base_settings_data(debug=True, openai_api_key="override-process")
    )
    env_values = {"OPENAI_API_KEY": "from-env-file"}

    caplog.set_level(logging.WARNING, logger="api")
    print_settings._log_overrides(settings, env_values)

    override_records = [
        record
        for record in caplog.records
        if isinstance(getattr(record, "msg", None), dict)
        and record.msg.get("event") == "settings_override_detected"
    ]
    assert override_records, "Expected override warning when process env differs from .env"


def test_ingestion_config_prefers_settings(monkeypatch, tmp_path):
    env_watch = tmp_path / "env_watch"
    env_temp = tmp_path / "env_temp"
    monkeypatch.setenv("INGESTION_WATCH_DIR", str(env_watch))
    monkeypatch.setenv("INGESTION_TEMP_DIR", str(env_temp))

    settings_watch = tmp_path / "settings_watch"
    settings_temp = tmp_path / "settings_temp"
    settings = Settings.model_validate(
        _base_settings_data(
            ingestion_watch_dir=str(settings_watch),
            ingestion_temp_dir=str(settings_temp),
        )
    )

    cfg = IngestionConfig.from_env(settings)

    assert cfg.watch_dir == settings_watch.resolve()
    assert cfg.temp_dir == settings_temp.resolve()
    assert settings_watch.exists()
    assert settings_temp.exists()


def test_ingestion_config_uses_env_when_settings_absent(monkeypatch, tmp_path):
    env_watch = tmp_path / "env_watch"
    env_temp = tmp_path / "env_temp"
    monkeypatch.setenv("INGESTION_WATCH_DIR", str(env_watch))
    monkeypatch.setenv("INGESTION_TEMP_DIR", str(env_temp))

    settings = Settings.model_validate(_base_settings_data())
    cfg = IngestionConfig.from_env(settings)

    assert cfg.watch_dir == env_watch.resolve()
    assert cfg.temp_dir == env_temp.resolve()
    assert env_watch.exists()
    assert env_temp.exists()


def test_ingestion_config_defaults_when_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("INGESTION_WATCH_DIR", raising=False)
    monkeypatch.delenv("INGESTION_TEMP_DIR", raising=False)

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        settings = Settings.model_validate(_base_settings_data())
        cfg = IngestionConfig.from_env(settings)
    finally:
        os.chdir(cwd)

    assert cfg.watch_dir == (tmp_path / "ingestion/watch").resolve()
    assert cfg.temp_dir == (tmp_path / "ingestion/temp").resolve()
    assert cfg.watch_dir.exists()
    assert cfg.temp_dir.exists()


@pytest.mark.parametrize(
    ("environment", "timeout", "should_warn"),
    [
        ("development", 15, True),
        ("dev", 19, True),
        ("production", 9, True),
        ("staging", 12, False),
        ("production", 12, False),
    ],
)
def test_classification_timeout_validator(environment, timeout, should_warn, caplog):
    caplog.set_level(logging.WARNING, logger="api")
    Settings.model_validate(
        _base_settings_data(
            environment=environment,
            classification_timeout_seconds=timeout,
        )
    )
    warnings = [
        record
        for record in caplog.records
        if isinstance(getattr(record, "msg", None), dict)
        and record.msg.get("event") == "classification_timeout_below_recommended"
    ]
    if should_warn:
        assert warnings, f"Expected warning for env={environment}, timeout={timeout}"
    else:
        assert not warnings, f"Did not expect warning for env={environment}, timeout={timeout}"


def test_discover_env_values_scans_files():
    values = print_settings._discover_env_values()
    assert isinstance(values, dict)


def test_print_settings_main_redacts(monkeypatch, capsys):
    secret = "sk-1234567890"
    env_secret = "sk-override9876"

    class DummySettings:
        debug = True

        def model_dump(self, mode: str = "python"):
            return {
                "openai_api_key": secret,
                "supabase_service_role_key": "srv-1234567890",
                "log_level": "INFO",
            }

    monkeypatch.setattr(print_settings, "Settings", lambda: DummySettings())
    monkeypatch.setattr(
        print_settings,
        "_discover_env_values",
        lambda: {"OPENAI_API_KEY": secret},
    )
    monkeypatch.setenv("OPENAI_API_KEY", env_secret)

    print_settings.main()

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["openai_api_key"].startswith(secret[:4])
    assert payload["openai_api_key"].endswith(secret[-2:])
    assert payload["supabase_service_role_key"].startswith("srv-")
    assert payload["supabase_service_role_key"].endswith("90")


def test_ensure_directory_permission_error(monkeypatch, caplog):
    import api.ingestion.config as ingestion_config

    class FakePath:
        def mkdir(self, parents=True, exist_ok=True):
            raise PermissionError("denied")

        def __str__(self):
            return "/forbidden"

        def __fspath__(self):
            return "/forbidden"

    caplog.set_level(logging.ERROR, logger="api")
    with pytest.raises(PermissionError):
        ingestion_config.IngestionConfig._ensure_directory(FakePath())

    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "ingestion_directory_permission_error"
        for record in caplog.records
    )


def test_ensure_directory_not_writable(monkeypatch, caplog):
    import api.ingestion.config as ingestion_config

    class FakePath:
        def mkdir(self, parents=True, exist_ok=True):
            return None

        def __str__(self):
            return "/readonly"

        def __fspath__(self):
            return "/readonly"

    caplog.set_level(logging.ERROR, logger="api")
    monkeypatch.setattr(ingestion_config.os, "access", lambda path, mode: False)

    with pytest.raises(PermissionError):
        ingestion_config.IngestionConfig._ensure_directory(FakePath())

    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "ingestion_directory_not_writable"
        for record in caplog.records
    )
