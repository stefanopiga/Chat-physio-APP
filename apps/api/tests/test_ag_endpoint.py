from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def _auth(monkeypatch, role="authenticated"):
    def fake_verify_jwt_token(_=None):
        return {"role": role, "sub": "user-1"}

    monkeypatch.setattr("api.dependencies.verify_jwt_token", lambda: fake_verify_jwt_token(None))


def test_ag_endpoint_requires_auth():
    resp = client.post(
        "/api/v1/chat/sessions/s1/messages",
        json={"message": "q"},
    )
    assert resp.status_code == 401


def test_ag_endpoint_validates_inputs(monkeypatch):
    _auth(monkeypatch)
    resp = client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={"message": ""},
    )
    assert resp.status_code == 400
    assert resp.json().get("detail") == "message mancante"


def test_ag_endpoint_runs_semantic_search_when_chunks_missing(monkeypatch):
    _auth(monkeypatch)

    call_state = {}

    def fake_search(query: str, match_count: int = 8, match_threshold=None):
        call_state["called"] = True
        call_state["query"] = query
        call_state["match_count"] = match_count
        call_state["match_threshold"] = match_threshold
        return [
            {
                "content": "contenuto chunk",
                "metadata": {"id": "chunk-1", "document_id": "doc-1"},
                "similarity_score": 0.91,
            }
        ]

    def fake_get_llm(_settings=None):
        raise RuntimeError("llm disabled for test")

    monkeypatch.setattr("api.routers.chat.perform_semantic_search", fake_search)
    monkeypatch.setattr("api.services.chat_service.get_llm", fake_get_llm)

    resp = client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={"message": "Quali esercizi posso fare?"},
    )

    assert resp.status_code == 200
    assert call_state.get("called") is True
    assert call_state.get("query") == "Quali esercizi posso fare?"
    data = resp.json()
    assert data["message_id"]
    message_text = (data["message"] or data["answer"] or "").lower()
    assert message_text
    assert "estratti" in message_text or "contesto non sufficiente" in message_text
    assert data["retrieval_time_ms"] >= 0
    assert data["generation_time_ms"] == 0
    citation_ids = {c.get("chunk_id") for c in data.get("citations", []) if c.get("chunk_id")}
    assert "chunk-1" in citation_ids


def test_ag_endpoint_fallback_generates_answer_and_citations_with_precomputed_chunks(monkeypatch):
    _auth(monkeypatch)

    def fake_get_llm(_settings=None):
        raise RuntimeError("llm disabled for test")

    monkeypatch.setattr("api.services.chat_service.get_llm", fake_get_llm)

    resp = client.post(
        "/api/v1/chat/sessions/s1/messages",
        headers={"Authorization": "Bearer x"},
        json={
            "message": "q",
            "chunks": [
                {"id": "c1", "document_id": "d1", "content": "t1"},
                {"id": None, "document_id": "d2", "content": "t2"},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("message_id")
    assert data["retrieval_time_ms"] == 0
    assert data["generation_time_ms"] == 0
    message_text = (data.get("message") or data.get("answer") or "").lower()
    assert message_text
    assert "estratti" in message_text or "contesto non sufficiente" in message_text
    citations = data.get("citations") or []
    citation_ids = {c.get("chunk_id") for c in citations if c.get("chunk_id")}
    assert citation_ids >= {"c1", "d2"}
