"""
Test suite per Admin Router (Story 4.1 + 4.2).

Coverage:
- POST /api/v1/admin/debug/query
- GET /api/v1/admin/analytics  
- GET /api/admin/me
- Authorization (admin only)
- Rate limiting
- Audit logging
"""
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status


# =============================================================================
# Test Admin Debug Query (Story 4.1)
# =============================================================================

def test_admin_debug_query_without_jwt_returns_401(client_no_auth):
    """TC-050: richiesta senza token → 401."""
    response = client_no_auth.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 401
    assert "Missing Bearer token" in response.json()["detail"]


@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
def test_admin_debug_query_with_student_jwt_returns_403(
    mock_llm, mock_search, client_student
):
    """TC-051: JWT student → 403 Forbidden."""
    response = client_student.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    assert "admin only" in response.json()["detail"].lower()
    
    mock_search.assert_not_called()


@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
def test_admin_debug_query_with_admin_jwt_returns_200(
    mock_llm, mock_search, client_admin
):
    """TC-052: JWT admin → 200 OK con response strutturata."""
    mock_search.return_value = [
        {
            "content": "Test chunk content",
            "score": 0.95,
            "metadata": {
                "id": "chunk_1",
                "document_id": "doc_1",
                "document_name": "test.pdf",
                "page_number": 1,
                "chunking_strategy": "recursive"
            }
        }
    ]
    
    mock_parser = MagicMock()
    mock_parser.invoke.return_value = "Test answer from LLM"
    
    mock_llm_instance = MagicMock()
    mock_llm_instance.__or__ = lambda self, other: mock_parser
    
    mock_llm.return_value = mock_llm_instance
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["question"] == "Test query"
    assert data["answer"] is not None
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["similarity_score"] == 0.95
    assert "retrieval_time_ms" in data
    assert "generation_time_ms" in data


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4)"
)
@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
def test_rate_limiting_11th_request_returns_429(
    mock_llm, mock_search
):
    """TC-080: Rate limiting 10 richieste/ora per admin."""
    # Create dedicated client con store isolato per evitare pollution da test precedenti
    from fastapi.testclient import TestClient
    from api.main import app
    from api.services.rate_limit_service import rate_limit_service
    from api import dependencies
    
    # Pulisci completamente rate limit store
    rate_limit_service._store.clear()
    
    # Mock admin auth
    def mock_verify_jwt_admin():
        return {"sub": "admin-test-rl", "role": "admin", "app_metadata": {"role": "admin"}}
    
    app.dependency_overrides[dependencies.verify_jwt_token] = lambda: mock_verify_jwt_admin()
    app.dependency_overrides[dependencies._auth_bridge] = lambda: mock_verify_jwt_admin()
    
    mock_search.return_value = []
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Answer"
    mock_llm.return_value = mock_chain
    
    with TestClient(app) as client_isolated:
        # 10 richieste OK
        for i in range(10):
            response = client_isolated.post(
                "/api/v1/admin/debug/query",
                json={"question": f"Test query {i}"}
            )
            assert response.status_code == 200, f"Request {i+1} failed with {response.status_code}"
        
        # 11ª richiesta bloccata
        response = client_isolated.post(
            "/api/v1/admin/debug/query",
            json={"question": "Test query 11"}
        )
        
        assert response.status_code == 429
    
    # Cleanup
    rate_limit_service._store.clear()
    app.dependency_overrides.clear()


def test_admin_debug_query_with_empty_question_returns_400(client_admin):
    """BT-005: domanda vuota → 400."""
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": ""}
    )
    assert response.status_code == 400
    assert "question" in response.json()["detail"].lower()
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "   "}
    )
    assert response.status_code == 400


@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
def test_admin_debug_query_with_no_results_returns_200_empty_chunks(
    mock_llm, mock_search, client_admin
):
    """BT-020: Zero risultati → 200 con chunks=[]."""
    mock_search.return_value = []
    
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Non trovato nel contesto"
    mock_llm.return_value = mock_chain
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Query senza risultati"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["chunks"] == []
    assert "non trovato" in data["answer"].lower() or "fallback" in data["answer"].lower()


@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
def test_admin_debug_query_with_llm_failure_returns_fallback(
    mock_llm, mock_search, client_admin
):
    """BT-030: LLM failure → fallback answer."""
    mock_search.return_value = [
        {
            "content": "Test content",
            "score": 0.9,
            "metadata": {
                "id": "chunk_1",
                "document_id": "doc_1",
                "document_name": "test.pdf",
                "page_number": 1,
                "chunking_strategy": "recursive"
            }
        }
    ]
    
    mock_chain = MagicMock()
    mock_chain.invoke.side_effect = Exception("LLM API error")
    mock_llm.return_value = mock_chain
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["answer"] is not None
    assert len(data["chunks"]) == 1


@patch('api.routers.admin.perform_semantic_search')
@patch('api.services.chat_service.get_llm')
@patch('api.routers.admin.logger')
def test_admin_debug_query_logs_audit_event(
    mock_logger, mock_llm, mock_search, client_admin
):
    """Audit logging: event logged con user_id, timing."""
    mock_search.return_value = []
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Answer"
    mock_llm.return_value = mock_chain
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test audit"}
    )
    
    assert response.status_code == 200
    
    mock_logger.info.assert_called()
    
    audit_calls = [
        call for call in mock_logger.info.call_args_list
        if call[0] and isinstance(call[0][0], dict) and call[0][0].get("event") == "admin_debug_query"
    ]
    
    assert len(audit_calls) > 0
    
    audit_log = audit_calls[0][0][0]
    assert audit_log["event"] == "admin_debug_query"
    assert "user_id" in audit_log
    assert "chunks_count" in audit_log


# =============================================================================
# Test Analytics Endpoint (Story 4.2)
# =============================================================================

def test_analytics_endpoint_403_for_non_admin(client_student):
    """Endpoint 403 per utente non-admin."""
    response = client_student.get("/api/v1/admin/analytics")
    
    assert response.status_code == 403
    assert response.json().get("detail") == "Forbidden: admin only"


def test_analytics_endpoint_200_for_admin(client_admin):
    """Endpoint 200 per admin con response valida."""
    response = client_admin.get("/api/v1/admin/analytics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "overview" in data
    assert "top_queries" in data
    assert "feedback_summary" in data
    assert "performance_metrics" in data
    
    assert "total_queries" in data["overview"]
    assert "total_sessions" in data["overview"]


def test_session_id_anonymization_no_exposure():
    """Session ID non esposto in response analytics."""
    from api.services.analytics_service import aggregate_analytics
    
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
    
    import json
    response_json = json.dumps(result.dict())
    
    assert "raw_session_abc123" not in response_json
    assert "sensitive_session_xyz789" not in response_json
    
    assert result.overview.total_queries == 2
    assert result.overview.total_sessions == 2


@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4)"
)
def test_rate_limiting_analytics_enforcement(client_admin):
    """Rate limiting 30 richieste/ora per analytics."""
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
            if "429" in str(e) or "rate limit" in str(e).lower():
                rate_limited = True
                break
    
    assert rate_limited or success_count <= 30

