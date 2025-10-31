"""
Test suite per Knowledge Base Router (Story 2.2 + 2.4 + 2.5).

Coverage:
- POST /classify (classification endpoint)
- POST /api/v1/knowledge-base/search
- POST /api/v1/admin/knowledge-base/sync-jobs
- GET /api/v1/admin/knowledge-base/sync-jobs/{job_id}
"""
from unittest.mock import patch
from api.ingestion.models import ClassificazioneOutput, DocumentStructureCategory


# =============================================================================
# Test Classification (Story 2.2)
# =============================================================================

def test_classify_endpoint_with_mock(monkeypatch, test_client):
    """Test: POST /classify con mock LLM."""
    class FakeChain:
        def invoke(self, _):
            return ClassificazioneOutput(
                classificazione=DocumentStructureCategory.DOCUMENTO_TABELLARE,
                motivazione="contiene molte tabelle",
                confidenza=0.9,
            )

    def fake_get_llm():
        return object()

    def fake_build_chain(_):
        return FakeChain()

    monkeypatch.setattr("api.routers.knowledge_base._get_llm", fake_get_llm)
    monkeypatch.setattr("api.routers.knowledge_base._build_classification_chain", fake_build_chain)

    resp = test_client.post("/classify", json={"testo": "Tabella 1: valori ..."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["classificazione"] == DocumentStructureCategory.DOCUMENTO_TABELLARE.value
    assert data["motivazione"]
    assert 0.0 <= data["confidenza"] <= 1.0


def test_classify_bad_request(test_client):
    """Test: POST /classify con testo vuoto → 400."""
    resp = test_client.post("/classify", json={"testo": "   "})
    assert resp.status_code == 400


# =============================================================================
# Test Knowledge Base Search (Story 2.4)
# =============================================================================

@patch('api.routers.knowledge_base.perform_semantic_search')
def test_search_endpoint_authenticated(mock_search, monkeypatch, test_client):
    """Test: POST /api/v1/knowledge-base/search authenticated."""
    def fake_verify_jwt_token(_=None):
        return {"role": "authenticated", "sub": "user-1"}
    
    monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))
    
    mock_search.return_value = [
        {
            "content": "Test content",
            "similarity_score": 0.92,  # Story 5.4.1 Phase 4: renamed from score
            "metadata": {
                "id": "chunk_1",
                "document_id": "doc_1",
                "document_name": "test.pdf"
            }
        }
    ]
    
    response = test_client.post(
        "/api/v1/knowledge-base/search",
        headers={"Authorization": "Bearer x"},
        json={"query": "test query", "match_count": 5, "match_threshold": 0.6}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["content"] == "Test content"
    assert data["results"][0]["similarity_score"] == 0.92
    mock_search.assert_called_once_with("test query", 5, 0.6)


@patch('api.routers.knowledge_base.perform_semantic_search')
def test_search_endpoint_public_access(mock_search, test_client):
    """Test: POST /api/v1/knowledge-base/search è pubblico (no auth required)."""
    mock_search.return_value = []
    
    response = test_client.post(
        "/api/v1/knowledge-base/search",
        json={"query": "test query"}
    )
    
    # Endpoint pubblico, deve funzionare senza auth
    assert response.status_code == 200
    assert "results" in response.json()


# =============================================================================
# Test Sync Jobs (Story 2.4 + 2.5)
# =============================================================================
# NOTE (Story 5.5): 3 test obsoleti rimossi - funzioni start_ingestion_job/get_job_status 
# rimosse in Story 5.2 refactoring. Endpoint signature cambiato in Story 2.5.

