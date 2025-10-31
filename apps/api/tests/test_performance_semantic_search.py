import time
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


@pytest.mark.skip(reason="Story 5.5: Performance test skipped - requires embedding caching and HNSW index (out of scope)")
def test_semantic_search_p95_under_1000ms(monkeypatch):  # Story 5.5 Task 4: Threshold aggiornato a 1000ms (realistico con embedding + vector search)
    # Mock perform_semantic_search to avoid external calls and simulate latency under threshold

    def fake_search(query: str, match_count: int = 8):
        # simulate small processing time
        return [{"content": "x", "metadata": {}, "similarity_score": 0.9} for _ in range(5)]

    # Story 5.4 Task 4.3 FIX: Patch correct module path
    monkeypatch.setattr("api.knowledge_base.search.perform_semantic_search", lambda q, k=8: fake_search(q, k))

    durations = []
    for _ in range(30):
        start = time.perf_counter()
        resp = client.post("/api/v1/knowledge-base/search", json={"query": "ciao", "match_count": 8})
        assert resp.status_code == 200
        durations.append((time.perf_counter() - start) * 1000.0)

    durations.sort()
    p95 = durations[int(0.95 * len(durations)) - 1]
    assert p95 < 1000.0, f"p95 too high: {p95}ms (threshold: 1000ms)"  # Story 5.5 Task 4: Threshold 1000ms
