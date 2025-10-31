"""
Unit tests - Analytics Dashboard (Story 4.2)

Test cases (9 totali):
1. BT-001: Aggregation: conteggio query corretto con normalizzazione case-insensitive
2. BT-002: Aggregation: top queries ordinati per count decrescente
3. BT-003: Aggregation: feedback ratio 0.0 quando zero feedback
4. BT-004: Aggregation: feedback ratio corretto con mix up/down
5. BT-005: Security: endpoint 403 per utente non-admin
6. BT-006 (Integration): Endpoint 200 per admin con response valida
7. BT-006 (Security): Session ID non esposto in response (privacy R-4.2-2)
8. BT-021: Rate limiting 30 richieste/ora enforcement
9. BT-020: Performance: aggregation completa < 500ms (benchmark con 1000 messaggi mock)

Migration Notes (Story 5.3):
- Migrated to modern fixture pattern (client_admin, client_student)
- Removed manual TestClient(app) and dependency_overrides
- Cleanup rate limit store handled by fixtures
"""

import os
import time
import pytest
from api.stores import chat_messages_store
from api.analytics.analytics import aggregate_analytics


def test_aggregation_query_count_case_insensitive():
    """BT-001: Conteggio query con normalizzazione case-insensitive."""
    # Setup: store con query duplicate case-insensitive
    test_store = {
        "session1": [
            {"role": "user", "content": "Test Query", "created_at": "2025-10-02T10:00:00Z"},
            {"role": "assistant", "content": "Answer", "created_at": "2025-10-02T10:00:01Z"},
        ],
        "session2": [
            {"role": "user", "content": "test query", "created_at": "2025-10-02T11:00:00Z"},
            {"role": "assistant", "content": "Answer", "created_at": "2025-10-02T11:00:01Z"},
        ],
        "session3": [
            {"role": "user", "content": "Another Query", "created_at": "2025-10-02T12:00:00Z"},
        ],
    }
    
    result = aggregate_analytics(
        chat_messages_store=test_store,
        feedback_store={},
        ag_latency_samples_ms=[],
    )
    
    # Assert: "Test Query" e "test query" contati come stesso (case-insensitive)
    assert result.overview.total_queries == 3
    assert result.overview.total_sessions == 3
    
    # Verifica top_queries contiene "test query" con count=2
    query_counts = {q.query_text: q.count for q in result.top_queries}
    assert query_counts.get("test query") == 2
    assert query_counts.get("another query") == 1


def test_aggregation_top_queries_sorted_descending():
    """BT-002: Top queries ordinati per count decrescente."""
    test_store = {
        "s1": [
            {"role": "user", "content": "Query A", "created_at": "2025-10-02T10:00:00Z"},
            {"role": "user", "content": "Query B", "created_at": "2025-10-02T10:01:00Z"},
            {"role": "user", "content": "Query A", "created_at": "2025-10-02T10:02:00Z"},
            {"role": "user", "content": "Query C", "created_at": "2025-10-02T10:03:00Z"},
            {"role": "user", "content": "Query A", "created_at": "2025-10-02T10:04:00Z"},
            {"role": "user", "content": "Query B", "created_at": "2025-10-02T10:05:00Z"},
        ],
    }
    
    result = aggregate_analytics(
        chat_messages_store=test_store,
        feedback_store={},
        ag_latency_samples_ms=[],
    )
    
    # Assert: Query A (3), Query B (2), Query C (1) - ordinati decrescente
    assert len(result.top_queries) == 3
    assert result.top_queries[0].query_text == "query a"
    assert result.top_queries[0].count == 3
    assert result.top_queries[1].query_text == "query b"
    assert result.top_queries[1].count == 2
    assert result.top_queries[2].query_text == "query c"
    assert result.top_queries[2].count == 1


def test_aggregation_feedback_ratio_zero_when_no_feedback():
    """BT-003: Feedback ratio 0.0 quando zero feedback."""
    result = aggregate_analytics(
        chat_messages_store={},
        feedback_store={},
        ag_latency_samples_ms=[],
    )
    
    assert result.feedback_summary.thumbs_up == 0
    assert result.feedback_summary.thumbs_down == 0
    assert result.feedback_summary.ratio == 0.0


def test_aggregation_feedback_ratio_correct_calculation():
    """BT-004: Feedback ratio corretto con mix up/down."""
    test_feedback = {
        "s1:m1": {"vote": "up", "session_id": "s1", "message_id": "m1"},
        "s1:m2": {"vote": "up", "session_id": "s1", "message_id": "m2"},
        "s1:m3": {"vote": "up", "session_id": "s1", "message_id": "m3"},
        "s2:m1": {"vote": "down", "session_id": "s2", "message_id": "m1"},
    }
    
    result = aggregate_analytics(
        chat_messages_store={},
        feedback_store=test_feedback,
        ag_latency_samples_ms=[],
    )
    
    assert result.feedback_summary.thumbs_up == 3
    assert result.feedback_summary.thumbs_down == 1
    # Ratio = 3/(3+1) = 0.75
    assert result.feedback_summary.ratio == 0.75


def test_analytics_endpoint_403_for_non_admin(client_student):
    """BT-005: Endpoint 403 per utente non-admin."""
    response = client_student.get("/api/v1/admin/analytics")
    
    assert response.status_code == 403
    assert response.json().get("detail") == "Forbidden: admin only"


def test_analytics_endpoint_200_for_admin():
    """BT-006: Endpoint 200 per admin con response valida."""
    from fastapi.testclient import TestClient
    from api.main import app
    from api import dependencies
    from unittest.mock import patch
    
    # Mock admin auth
    def mock_verify_jwt_admin():
        return {"sub": "admin-123", "role": "admin", "app_metadata": {"role": "admin"}}
    
    # Setup dati mock per aggregate_analytics
    test_store = {
        "test_session": [
            {"role": "user", "content": "Test query", "created_at": "2025-10-02T10:00:00Z"},
        ]
    }
    test_feedback = {"test:m1": {"vote": "up", "session_id": "test", "message_id": "m1"}}
    test_latency = [100, 200, 300]
    
    # Mock aggregate_analytics per iniettare dati test
    with patch('api.routers.admin.aggregate_analytics') as mock_agg:
        # Chiama funzione reale con dati test
        from api.analytics.analytics import aggregate_analytics
        mock_agg.return_value = aggregate_analytics(
            chat_messages_store=test_store,
            feedback_store=test_feedback,
            ag_latency_samples_ms=test_latency
        )
        
        # Override auth
        app.dependency_overrides[dependencies.verify_jwt_token] = lambda: mock_verify_jwt_admin()
        app.dependency_overrides[dependencies._auth_bridge] = lambda: mock_verify_jwt_admin()
        
        try:
            with TestClient(app) as client:
                response = client.get("/api/v1/admin/analytics")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verifica struttura response
                assert "overview" in data
                assert "top_queries" in data
                assert "feedback_summary" in data
                assert "performance_metrics" in data
                
                # Verifica overview
                assert data["overview"]["total_queries"] >= 1
                assert data["overview"]["total_sessions"] >= 1
                
                # Verifica feedback
                assert data["feedback_summary"]["thumbs_up"] >= 1
                
                # Verifica performance
                assert "latency_p95_ms" in data["performance_metrics"]
                assert "latency_p99_ms" in data["performance_metrics"]
        finally:
            app.dependency_overrides.clear()


def test_session_id_anonymization_no_exposure():
    """BT-006: Session ID non esposto in response analytics (privacy R-4.2-2)."""
    # Setup: store con session_id riconoscibili
    test_store = {
        "raw_session_abc123": [
            {"role": "user", "content": "Test query 1", "created_at": "2025-10-02T10:00:00Z"},
        ],
        "sensitive_session_xyz789": [
            {"role": "user", "content": "Test query 2", "created_at": "2025-10-02T11:00:00Z"},
        ],
    }
    
    result = aggregate_analytics(
        chat_messages_store=test_store,
        feedback_store={},
        ag_latency_samples_ms=[100, 200],
    )
    
    # Serializza response per verificare nessun leak di session_id
    import json
    response_json = json.dumps(result.dict())
    
    # Assert: NO raw session_id presenti
    assert "raw_session_abc123" not in response_json, "Session ID raw esposto in response"
    assert "sensitive_session_xyz789" not in response_json, "Session ID raw esposto in response"
    
    # Verifica che dati aggregati siano presenti (no full suppression)
    assert result.overview.total_queries == 2
    assert result.overview.total_sessions == 2
    
    # Verifica che top_queries non contiene session_id
    for query_stat in result.top_queries:
        assert hasattr(query_stat, 'query_text')
        assert hasattr(query_stat, 'count')
        assert hasattr(query_stat, 'last_queried_at')
        # Nessun campo session_id deve esistere
        assert not hasattr(query_stat, 'session_id'), "Query stat espone session_id"


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4)"
)
def test_rate_limiting_enforcement(client_admin):
    """BT-021: Rate limiting 30 richieste/ora per endpoint analytics."""
    
    # Setup dati minimi
    chat_messages_store["rl_test"] = [
        {"role": "user", "content": "Test", "created_at": "2025-10-02T10:00:00Z"},
    ]
    
    try:
        # Simula 31 richieste consecutive
        success_count = 0
        rate_limited = False
        
        for i in range(31):
            try:
                response = client_admin.get("/api/v1/admin/analytics")
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited = True
                    break
            except Exception as e:
                # Rate limit può sollevare eccezione
                if "429" in str(e) or "rate limit" in str(e).lower():
                    rate_limited = True
                    break
        
        # Assert: almeno alcune richieste riuscite, poi rate limited
        # Nota: test può essere flaky se altri test hanno usato stesso limiter
        # Verifica che rate limiting è configurato (response code o exception)
        assert rate_limited or success_count <= 30, \
            f"Rate limiting non attivo: {success_count} richieste OK senza blocco"
        
    finally:
        if "rl_test" in chat_messages_store:
            del chat_messages_store["rl_test"]


def test_aggregation_performance_benchmark():
    """BT-020: Performance benchmark aggregation < 500ms con 1000 messaggi."""
    # Setup: 1000 messaggi mock distribuiti su 50 sessioni
    large_store = {}
    for i in range(50):
        session_id = f"session_{i}"
        messages = []
        for j in range(20):
            messages.append({
                "role": "user",
                "content": f"Query {j % 10}",
                "created_at": f"2025-10-02T{10+j%24:02d}:00:00Z",
            })
            messages.append({
                "role": "assistant",
                "content": f"Answer {j}",
                "created_at": f"2025-10-02T{10+j%24:02d}:00:01Z",
            })
        large_store[session_id] = messages
    
    # Setup feedback (100 votes)
    large_feedback = {
        f"s{i}:m{j}": {"vote": "up" if i % 2 == 0 else "down"}
        for i in range(50)
        for j in range(2)
    }
    
    # Setup latency samples (200 samples)
    large_latency = list(range(100, 300))
    
    # Benchmark
    start_time = time.time()
    result = aggregate_analytics(
        chat_messages_store=large_store,
        feedback_store=large_feedback,
        ag_latency_samples_ms=large_latency,
    )
    duration_ms = int((time.time() - start_time) * 1000)
    
    # Assert: aggregation completa < 500ms
    assert duration_ms < 500, f"Aggregation took {duration_ms}ms, expected < 500ms"
    
    # Verifica correttezza aggregazione
    assert result.overview.total_queries == 1000  # 50 sessions * 20 user messages
    assert result.overview.total_sessions == 50
    assert len(result.top_queries) <= 10  # Top 10
    assert result.feedback_summary.thumbs_up + result.feedback_summary.thumbs_down == 100

