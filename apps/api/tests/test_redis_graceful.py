import logging


from api.config import Settings
from api.diagnostics import redis_check


def _base_settings_data(**overrides) -> dict:
    data = {
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "service-key",
        "supabase_jwt_secret": "jwt-secret",
        "openai_api_key": "sk-test",
    }
    data.update(overrides)
    return data


def test_check_redis_health_disabled_skips(monkeypatch, caplog):
    settings = Settings.model_validate(
        _base_settings_data(classification_cache_enabled=False)
    )
    called = False

    def fail_if_called(_settings):
        nonlocal called
        called = True
        raise AssertionError("get_classification_cache should not be invoked when disabled")

    monkeypatch.setattr(redis_check, "get_classification_cache", fail_if_called)

    caplog.set_level(logging.INFO, logger="api")
    result = redis_check.check_redis_health(settings)

    assert result["enabled"] is False
    assert result["healthy"] is True
    assert result["redis_url"] is None
    assert called is False
    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "redis_health_skipped"
        for record in caplog.records
    )


def test_check_redis_health_logs_warning_on_failure(monkeypatch, caplog):
    class DummyClient:
        def ping(self):
            raise redis_check.RedisError("connection refused")

    class DummyCache:
        def __init__(self):
            self._redis = DummyClient()
            self.enabled = True

    settings = Settings.model_validate(_base_settings_data())
    monkeypatch.setattr(
        redis_check, "get_classification_cache", lambda _settings: DummyCache()
    )
    monkeypatch.setattr(
        redis_check, "resolve_cache_url", lambda _settings: "redis://test"
    )

    caplog.set_level(logging.WARNING, logger="api")
    result = redis_check.check_redis_health(settings)

    assert result["healthy"] is False
    assert result["enabled"] is True
    assert result["redis_url"] == "redis://test"
    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "redis_health_failed"
        for record in caplog.records
    )


def test_check_redis_health_success(monkeypatch, caplog):
    class DummyClient:
        def ping(self):
            return True

    class DummyCache:
        def __init__(self):
            self._redis = DummyClient()
            self.enabled = True

    settings = Settings.model_validate(_base_settings_data())
    monkeypatch.setattr(
        redis_check, "get_classification_cache", lambda _settings: DummyCache()
    )
    monkeypatch.setattr(
        redis_check, "resolve_cache_url", lambda _settings: "redis://test"
    )

    caplog.set_level(logging.INFO, logger="api")
    result = redis_check.check_redis_health(settings)

    assert result["healthy"] is True
    assert result["latency_ms"] >= 0
    assert any(
        isinstance(record.msg, dict)
        and record.msg.get("event") == "redis_health_ok"
        for record in caplog.records
    )

