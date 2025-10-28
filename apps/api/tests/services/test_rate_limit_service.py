"""
Test suite per Rate Limit Service.

Coverage:
- RateLimitService.enforce_rate_limit()
- Window expiration
- Multiple keys isolation

Note (Story 5.4.1 Phase 5):
- Tests skipped in test environment (TESTING=true, RATE_LIMITING_ENABLED=false)
- Rate limiting is disabled for test isolation
- Tests can be run with override fixture to enable RL locally
"""
import os
import pytest
import time
from datetime import datetime, timedelta


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4.1)"
)
def test_rate_limit_service_allows_within_limit():
    """Test: richieste entro limite passano."""
    from api.services.rate_limit_service import RateLimitService
    
    service = RateLimitService(store={})  # Isolated store per test
    key = "test_user_1"
    scope = "test_scope"
    
    # 10 richieste OK (limite 10) - nessuna HTTPException significa successo
    for i in range(10):
        try:
            service.enforce_rate_limit(
                key=key,
                scope=scope,
                max_requests=10,
                window_seconds=60
            )
        except Exception as e:
            pytest.fail(f"Request {i+1} should be allowed but raised: {e}")


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4.1)"
)
def test_rate_limit_service_blocks_over_limit():
    """Test: richiesta oltre limite bloccata."""
    from api.services.rate_limit_service import RateLimitService
    from fastapi import HTTPException
    
    service = RateLimitService(store={})  # Isolated store per test
    key = "test_user_2"
    scope = "test_scope"
    
    # 5 richieste OK
    for i in range(5):
        service.enforce_rate_limit(
            key=key,
            scope=scope,
            max_requests=5,
            window_seconds=60
        )
    
    # 6ª richiesta bloccata con HTTPException 429
    with pytest.raises(HTTPException) as exc_info:
        service.enforce_rate_limit(
            key=key,
            scope=scope,
            max_requests=5,
            window_seconds=60
        )
    assert exc_info.value.status_code == 429


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4.1)"
)
def test_rate_limit_service_window_expiration():
    """Test: window scaduta resetta counter."""
    from api.services.rate_limit_service import RateLimitService
    from fastapi import HTTPException
    
    service = RateLimitService(store={})  # Isolated store per test
    key = "test_user_3"
    scope = "test_scope"
    
    # 3 richieste entro window breve
    for i in range(3):
        service.enforce_rate_limit(
            key=key,
            scope=scope,
            max_requests=3,
            window_seconds=1  # 1 secondo window
        )
    
    # 4ª richiesta bloccata
    with pytest.raises(HTTPException) as exc_info:
        service.enforce_rate_limit(
            key=key,
            scope=scope,
            max_requests=3,
            window_seconds=1
        )
    assert exc_info.value.status_code == 429
    
    # Wait per window expiration
    time.sleep(1.1)
    
    # Dopo expiration: richiesta OK (reset)
    try:
        service.enforce_rate_limit(
            key=key,
            scope=scope,
            max_requests=3,
            window_seconds=1
        )
    except Exception as e:
        pytest.fail(f"Request after window expiration should be allowed but raised: {e}")


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4.1)"
)
def test_rate_limit_service_multiple_keys_isolated():
    """Test: rate limit per key isolati."""
    from api.services.rate_limit_service import RateLimitService
    from fastapi import HTTPException
    
    service = RateLimitService(store={})  # Isolated store per test
    scope = "test_scope"
    
    # User 1: 2 richieste OK
    for i in range(2):
        service.enforce_rate_limit(
            key="user_1",
            scope=scope,
            max_requests=2,
            window_seconds=60
        )
    
    # User 1: 3ª richiesta bloccata
    with pytest.raises(HTTPException) as exc_info:
        service.enforce_rate_limit(
            key="user_1",
            scope=scope,
            max_requests=2,
            window_seconds=60
        )
    assert exc_info.value.status_code == 429
    
    # User 2: prima richiesta OK (key diversa)
    try:
        service.enforce_rate_limit(
            key="user_2",
            scope=scope,
            max_requests=2,
            window_seconds=60
        )
    except Exception as e:
        pytest.fail(f"User 2 first request should be allowed but raised: {e}")

