"""
Test suite for /classify endpoint (Story 2.2).

Migration Notes (Story 5.3):
- Removed manual TestClient(app)
- Uses monkeypatch for mocking (compatible with pytest fixtures)
"""
from api.routers.knowledge_base import _build_classification_chain
from api.ingestion.models import ClassificazioneOutput, DocumentStructureCategory


def test_classify_endpoint_with_mock(client_no_auth, monkeypatch):
    """
    Test classify endpoint con mock chain LangChain.
    
    Note: client_no_auth usato perché /classify è pubblico (no auth).
    """
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

    # Monkeypatch LLM getter e builder per isolare dai provider reali (Story 5.2)
    monkeypatch.setattr("api.routers.knowledge_base._get_llm", fake_get_llm)
    monkeypatch.setattr("api.routers.knowledge_base._build_classification_chain", fake_build_chain)

    resp = client_no_auth.post("/classify", json={"testo": "Tabella 1: valori ..."})
    assert resp.status_code == 200
    data = resp.json()
    assert data["classificazione"] == DocumentStructureCategory.DOCUMENTO_TABELLARE.value
    assert data["motivazione"]
    assert 0.0 <= data["confidenza"] <= 1.0


def test_classify_bad_request(client_no_auth):
    """Test classify con input vuoto restituisce 400."""
    resp = client_no_auth.post("/classify", json={"testo": "   "})
    assert resp.status_code == 400

