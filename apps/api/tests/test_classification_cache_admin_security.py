"""
Security tests for classification cache admin endpoints.

Story 2.9: Classification Performance Optimization
QA Requirements: 2.9-SEC-001, 2.9-SEC-002

Tests:
- Authentication: endpoints require JWT
- Authorization: endpoints require admin role
- Rate limiting: endpoints enforce rate limits
"""
import time

import pytest


# ============================================================================
# 2.9-SEC-001: Authentication Tests
# ============================================================================


def test_cache_metrics_requires_authentication(client_no_auth) -> None:
    """2.9-SEC-001: GET /admin/knowledge-base/classification-cache/metrics requires JWT."""
    response = client_no_auth.get("/api/v1/admin/knowledge-base/classification-cache/metrics")
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "Missing Bearer token" in str(detail) or "Unauthorized" in str(detail)


def test_cache_flush_requires_authentication(client_no_auth) -> None:
    """2.9-SEC-001: DELETE /admin/knowledge-base/classification-cache requires JWT."""
    response = client_no_auth.delete("/api/v1/admin/knowledge-base/classification-cache")
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "Missing Bearer token" in str(detail) or "Unauthorized" in str(detail)


def test_cache_delete_entry_requires_authentication(client_no_auth) -> None:
    """2.9-SEC-001: DELETE /admin/knowledge-base/classification-cache/{digest} requires JWT."""
    response = client_no_auth.delete(
        "/api/v1/admin/knowledge-base/classification-cache/test123"
    )
    assert response.status_code == 401
    detail = response.json().get("detail", "")
    assert "Missing Bearer token" in str(detail) or "Unauthorized" in str(detail)


# ============================================================================
# 2.9-SEC-002: Authorization Tests (Admin-Only Access)
# ============================================================================


def test_cache_metrics_forbidden_for_non_admin(client_student) -> None:
    """2.9-SEC-002: GET metrics forbidden for non-admin users."""
    response = client_student.get(
        "/api/v1/admin/knowledge-base/classification-cache/metrics"
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_cache_flush_forbidden_for_non_admin(client_student) -> None:
    """2.9-SEC-002: DELETE flush forbidden for non-admin users."""
    response = client_student.delete(
        "/api/v1/admin/knowledge-base/classification-cache"
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_cache_delete_entry_forbidden_for_non_admin(client_student) -> None:
    """2.9-SEC-002: DELETE entry forbidden for non-admin users."""
    response = client_student.delete(
        "/api/v1/admin/knowledge-base/classification-cache/test123"
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


# ============================================================================
# 2.9-SEC-002: Admin Access (Positive Tests)
# ============================================================================


def test_cache_metrics_allowed_for_admin(client_admin) -> None:
    """2.9-SEC-002: GET metrics allowed for admin users."""
    response = client_admin.get(
        "/api/v1/admin/knowledge-base/classification-cache/metrics"
    )
    assert response.status_code == 200
    data = response.json()
    assert "cache" in data
    assert "enabled" in data["cache"]
    assert "hits" in data["cache"]
    assert "misses" in data["cache"]


def test_cache_flush_allowed_for_admin(client_admin) -> None:
    """2.9-SEC-002: DELETE flush allowed for admin users."""
    response = client_admin.delete(
        "/api/v1/admin/knowledge-base/classification-cache"
    )
    # Can be 200 (success) or 409 (cache disabled in test env)
    assert response.status_code in [200, 409]


def test_cache_delete_entry_allowed_for_admin(client_admin) -> None:
    """2.9-SEC-002: DELETE entry allowed for admin users."""
    response = client_admin.delete(
        "/api/v1/admin/knowledge-base/classification-cache/nonexistent123"
    )
    # Can be 404 (not found) or 409 (cache disabled)
    assert response.status_code in [404, 409]


# ============================================================================
# Rate Limiting Tests
# ============================================================================


@pytest.mark.skip(
    reason="Rate limiting disabled in test environment (conftest.py sets RATE_LIMITING_ENABLED=false)"
)
def test_cache_metrics_rate_limiting_enforcement(client_admin) -> None:
    """Verify rate limiting on cache metrics endpoint.
    
    Note: Skipped as rate limiting is disabled in test env for isolation.
    Manual testing required with rate limiting enabled.
    """
    endpoint = "/api/v1/admin/knowledge-base/classification-cache/metrics"

    # Make rapid requests to trigger rate limit
    success_count = 0
    rate_limited = False

    for _ in range(25):  # Exceed typical 20/min limit
        response = client_admin.get(endpoint)
        if response.status_code == 200:
            success_count += 1
        elif response.status_code == 429:
            rate_limited = True
            break

    # Should hit rate limit before 25 requests
    assert rate_limited or success_count <= 20, (
        f"Rate limiting not enforced: {success_count} requests succeeded without 429"
    )


@pytest.mark.skip(
    reason="Rate limiting disabled in test environment (conftest.py sets RATE_LIMITING_ENABLED=false)"
)
def test_cache_flush_rate_limiting_enforcement(client_admin) -> None:
    """Verify rate limiting on cache flush endpoint.
    
    Note: Skipped as rate limiting is disabled in test env for isolation.
    Manual testing required with rate limiting enabled.
    """
    endpoint = "/api/v1/admin/knowledge-base/classification-cache"

    success_count = 0
    rate_limited = False

    for _ in range(25):
        response = client_admin.delete(endpoint)
        if response.status_code in [200, 409]:  # 409 if cache disabled
            success_count += 1
        elif response.status_code == 429:
            rate_limited = True
            break
        time.sleep(0.1)  # Small delay to avoid overwhelming

    assert rate_limited or success_count <= 20, (
        f"Rate limiting not enforced: {success_count} requests succeeded without 429"
    )


# ============================================================================
# Integration: Security + Functionality
# ============================================================================


def test_cache_metrics_response_structure_for_admin(client_admin) -> None:
    """Verify admin can access metrics with complete response structure."""
    response = client_admin.get(
        "/api/v1/admin/knowledge-base/classification-cache/metrics"
    )
    assert response.status_code == 200

    data = response.json()
    cache = data["cache"]

    # Validate response structure
    assert isinstance(cache["enabled"], bool)
    assert isinstance(cache["hits"], int)
    assert isinstance(cache["misses"], int)
    assert isinstance(cache["errors"], int)
    assert cache["hit_rate"] is None or isinstance(cache["hit_rate"], (int, float))

    # Validate latency metrics structure
    assert "latency_ms" in cache
    assert "hit" in cache["latency_ms"]
    assert "miss" in cache["latency_ms"]


def test_cache_endpoints_respect_feature_flag(client_admin, monkeypatch) -> None:
    """Verify endpoints respect CLASSIFICATION_CACHE_ENABLED flag."""
    # Disable cache via environment
    monkeypatch.setenv("CLASSIFICATION_CACHE_ENABLED", "false")

    # Metrics should still work but show disabled state
    response = client_admin.get(
        "/api/v1/admin/knowledge-base/classification-cache/metrics"
    )
    # Endpoint may return 200 with enabled=false or 409 conflict
    assert response.status_code in [200, 409]

    # Flush should return conflict when disabled
    response = client_admin.delete(
        "/api/v1/admin/knowledge-base/classification-cache"
    )
    assert response.status_code == 409
    assert "disabled" in response.json()["detail"].lower()

