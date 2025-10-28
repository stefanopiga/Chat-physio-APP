import pytest
from fastapi import HTTPException

from api.services.rate_limit_service import RateLimitService


def test_rate_limit_service_blocks_after_threshold(monkeypatch):
    monkeypatch.setenv("TESTING", "false")
    monkeypatch.setenv("RATE_LIMITING_ENABLED", "true")

    times = iter([0, 1, 2, 65])
    monkeypatch.setattr("api.services.rate_limit_service.time.time", lambda: next(times))

    service = RateLimitService(store={})
    key = "user::1"
    scope = "chat_message"

    service.enforce_rate_limit(key, scope, window_seconds=60, max_requests=2)
    service.enforce_rate_limit(key, scope, window_seconds=60, max_requests=2)

    with pytest.raises(HTTPException) as exc:
        service.enforce_rate_limit(key, scope, window_seconds=60, max_requests=2)

    assert exc.value.status_code == 429

    service.enforce_rate_limit(key, scope, window_seconds=60, max_requests=2)
