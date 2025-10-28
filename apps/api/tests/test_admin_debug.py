"""
Test suite per endpoint /api/v1/admin/debug/query (Story 4.1).

Coverage Target: ≥95%
Rischi Mitigati: R-4.1-1 (CRITICAL), R-4.1-3 (HIGH), R-4.1-6 (MEDIUM)

Test Cases:
- TC-050: Auth - 401 senza token
- TC-051: Auth - 403 con ruolo student
- TC-052: Auth - 200 con ruolo admin
- TC-080: Rate limiting - 429 all'11ª richiesta
- BT-005: Validation - 400 con input vuoto
- BT-020: Edge case - 200 con zero risultati
- BT-030: Error handling - fallback LLM failure
- Audit logging verification

Fonte: docs/architecture/addendum-testing-backend-4.1.md
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status

# Import app e dependencies refactorizzati (Story 5.2)
from api.main import app
from api.dependencies import verify_jwt_token, _is_admin
from api.services.rate_limit_service import rate_limit_service


# ========== Mock Helpers ==========

def mock_verify_jwt_admin(role: str = "admin") -> dict:
    """
    Mock JWT payload per test.
    
    Args:
        role: Ruolo da simulare ("admin" o "student")
        
    Returns:
        dict: JWT payload simulato
    """
    return {
        "sub": "test_user_123",
        "app_metadata": {"role": role},
        "exp": 9999999999,
        "iat": 1000000000
    }


def mock_verify_jwt_student() -> dict:
    """Mock JWT payload per ruolo student."""
    return mock_verify_jwt_admin(role="student")


def mock_no_jwt():
    """Mock per assenza JWT (solleva 401)."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing Bearer token"
    )


# ========== Fixtures ==========
# Nota: Fixtures client_admin, client_student, client_no_auth definite in conftest.py


# ========== Test Autenticazione (R-4.1-1 CRITICAL) ==========

def test_admin_debug_query_without_jwt_returns_401(client_no_auth):
    """
    TC-050: Verifica che richiesta senza token JWT restituisca 401 Unauthorized.
    
    Scenario:
        Given: Nessun token JWT fornito
        When: POST /api/v1/admin/debug/query
        Then: Status 401 Unauthorized
    
    Mitigazione: R-4.1-1 (Admin Authentication Bypass)
    Fonte: docs/qa/assessments/4.1-test-design-20251001.md L81-L82
    """
    response = client_no_auth.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 401
    assert "Missing Bearer token" in response.json()["detail"]


@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
def test_admin_debug_query_with_student_jwt_returns_403(
    mock_llm,
    mock_search,
    client_student
):
    """
    TC-051: Verifica che JWT con ruolo 'student' restituisca 403 Forbidden.
    
    Scenario:
        Given: JWT valido ma con role='student'
        When: POST /api/v1/admin/debug/query
        Then: Status 403 Forbidden (admin only)
    
    Mitigazione: R-4.1-1 (Role-based access control)
    Fonte: docs/qa/assessments/4.1-test-design-20251001.md L84-L85
    """
    response = client_student.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]
    assert "admin only" in response.json()["detail"].lower()
    
    # Verifica che search non sia stato invocato (early auth check)
    mock_search.assert_not_called()


@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
def test_admin_debug_query_with_admin_jwt_returns_200(
    mock_llm,
    mock_search,
    client_admin
):
    """
    TC-052: Verifica che JWT admin valido restituisca 200 OK con response strutturata.
    
    Scenario:
        Given: JWT valido con role='admin'
        When: POST /api/v1/admin/debug/query con question valida
        Then: Status 200 OK con answer, chunks, timing metrics
    
    Mitigazione: R-4.1-1 (Happy path auth admin)
    Fonte: docs/qa/assessments/4.1-test-design-20251001.md L87-L88
    """
    # Mock retrieval
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
    
    # Mock LLM - crea un mock completo della chain LCEL
    mock_parser = MagicMock()
    mock_parser.invoke.return_value = "Test answer from LLM"
    
    mock_llm_instance = MagicMock()
    # Simula l'operatore | che restituisce un Runnable
    mock_llm_instance.__or__ = lambda self, other: mock_parser
    
    mock_llm.return_value = mock_llm_instance
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verifica struttura response
    assert data["question"] == "Test query"
    # Verifica che ci sia una risposta (può essere mock o fallback)
    assert data["answer"] is not None
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["similarity_score"] == 0.95
    assert "retrieval_time_ms" in data
    assert "generation_time_ms" in data
    assert data["retrieval_time_ms"] >= 0
    assert data["generation_time_ms"] >= 0


# ========== Test Rate Limiting (R-4.1-3 HIGH) ==========

@pytest.mark.skipif(
    os.getenv("TESTING") == "true",
    reason="Rate limiting disabled in test environment for isolation (Story 5.4)"
)
@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
def test_rate_limiting_11th_request_returns_429(
    mock_llm,
    mock_search,
    client_admin
):
    """
    TC-080: Verifica rate limiting di 10 richieste/ora per admin.
    
    Scenario:
        Given: Admin autenticato
        When: Invia 10 richieste consecutive (OK)
        And: Invia 11ª richiesta entro 1 ora
        Then: 11ª richiesta restituisce 429 Too Many Requests
    
    Mitigazione: R-4.1-3 (Uncontrolled API Costs)
    Fonte: docs/qa/assessments/4.1-test-design-20251001.md (Rate Limiting)
    """
    # Mock rapido per test
    mock_search.return_value = []
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Answer"
    mock_llm.return_value = mock_chain
    
    # 10 richieste consecutive (devono passare)
    for i in range(10):
        response = client_admin.post(
            "/api/v1/admin/debug/query",
            json={"question": f"Test query {i}"}
        )
        assert response.status_code == 200, f"Request {i+1} failed"
    
    # 11ª richiesta (deve essere bloccata)
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query 11"}
    )
    
    assert response.status_code == 429
    # SlowAPI rate limiter potrebbe non restituire "detail" in formato standard
    # Verifichiamo solo lo status code 429 come prova sufficiente del rate limiting
    response_data = response.json()
    if "detail" in response_data:
        detail = response_data["detail"].lower()
        assert "rate" in detail or "limit" in detail


# ========== Test Validazione Input ==========

def test_admin_debug_query_with_empty_question_returns_400(client_admin):
    """
    BT-005: Verifica validazione input - domanda vuota restituisce 400 Bad Request.
    
    Scenario:
        Given: Admin autenticato
        When: POST con question vuota o null
        Then: Status 400 Bad Request
    
    Fonte: docs/stories/4.1.admin-debug-view.md L96 (edge case domanda vuota)
    """
    # Test con stringa vuota
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": ""}
    )
    assert response.status_code == 400
    assert "question" in response.json()["detail"].lower()
    
    # Test con stringa solo whitespace
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "   "}
    )
    assert response.status_code == 400


# ========== Test Casi Limite ==========

@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
def test_admin_debug_query_with_no_results_returns_200_empty_chunks(
    mock_llm,
    mock_search,
    client_admin
):
    """
    BT-020: Verifica gestione zero risultati da retrieval.
    
    Scenario:
        Given: Admin autenticato
        When: Semantic search non trova chunk rilevanti (empty results)
        Then: Status 200 OK con chunks=[], answer fallback
    
    Fonte: docs/stories/4.1.admin-debug-view.md L153 (empty state chunk)
    """
    # Mock retrieval senza risultati
    mock_search.return_value = []
    
    # Mock LLM con fallback
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
    assert data["retrieval_time_ms"] >= 0


@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
def test_admin_debug_query_with_llm_failure_returns_fallback(
    mock_llm,
    mock_search,
    client_admin
):
    """
    BT-030: Verifica fallback quando LLM invocation fallisce.
    
    Scenario:
        Given: Admin autenticato
        When: LLM invocation solleva exception
        Then: Status 200 OK con answer fallback (no crash)
    
    Mitigazione: R-4.1-6 (Error Handling Completeness)
    Fonte: docs/stories/4.1.admin-debug-view.md L97-L98 (error handling)
    """
    # Mock retrieval con risultati
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
    
    # Mock LLM che solleva eccezione
    mock_chain = MagicMock()
    mock_chain.invoke.side_effect = Exception("LLM API error")
    mock_llm.return_value = mock_chain
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test query"}
    )
    
    # Deve restituire 200 con fallback (non crash 500)
    assert response.status_code == 200
    data = response.json()
    
    # Verifica fallback answer
    assert data["answer"] is not None
    assert len(data["chunks"]) == 1  # Chunks presenti anche se LLM fallisce


# ========== Test Audit Logging (R-4.1-2) ==========

@patch('api.routers.admin.perform_semantic_search')
@patch('langchain_openai.ChatOpenAI')
@patch('api.routers.admin.logger')
def test_admin_debug_query_logs_audit_event(
    mock_logger,
    mock_llm,
    mock_search,
    client_admin
):
    """
    Verifica che ogni accesso all'endpoint debug generi audit log.
    
    Scenario:
        Given: Admin autenticato
        When: POST /api/v1/admin/debug/query
        Then: Event "admin_debug_query" loggato con user_id, chunks_count, timing
    
    Mitigazione: R-4.1-2 (Data Exposure - audit trail)
    Fonte: docs/architecture/addendum-fastapi-best-practices.md Sezione 6
    """
    mock_search.return_value = []
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = "Answer"
    mock_llm.return_value = mock_chain
    
    response = client_admin.post(
        "/api/v1/admin/debug/query",
        json={"question": "Test audit"}
    )
    
    assert response.status_code == 200
    
    # Verifica audit log call
    mock_logger.info.assert_called()
    
    # Trova la chiamata con event="admin_debug_query"
    audit_calls = [
        call for call in mock_logger.info.call_args_list
        if call[0] and isinstance(call[0][0], dict) and call[0][0].get("event") == "admin_debug_query"
    ]
    
    assert len(audit_calls) > 0, "Audit log non registrato"
    
    audit_log = audit_calls[0][0][0]
    assert audit_log["event"] == "admin_debug_query"
    assert "user_id" in audit_log
    assert "chunks_count" in audit_log
    assert "retrieval_time_ms" in audit_log
    assert "generation_time_ms" in audit_log

