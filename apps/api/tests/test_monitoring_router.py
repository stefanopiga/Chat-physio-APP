import pytest
from fastapi.testclient import TestClient

from api.ingestion.watcher_metrics import reset_watcher_metrics
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_watcher_metrics_endpoint_json(client, monkeypatch):
    sample = {
        "documents_processed": 2,
        "classification": {
            "success": 2,
            "failure": 0,
            "skipped": 0,
            "success_ratio": 1.0,
            "failure_ratio": 0.0,
        },
        "classification_latency_ms": {"count": 2, "p50": 120.0, "p95": 200.0, "p99": 220.0},
        "fallback": {"count": 0, "ratio": 0.0},
        "strategy_distribution": {
            "counts": {"recursive_character_800_160": 2},
            "ratio": {"recursive_character_800_160": 1.0},
        },
        "classification_cache": {"enabled": True, "hit_rate": 0.5},
    }

    monkeypatch.setattr(
        "api.ingestion.watcher_metrics.get_watcher_metrics_snapshot",
        lambda settings: sample,
    )
    reset_watcher_metrics()

    response = client.get("/metrics/watcher")
    assert response.status_code == 200
    assert response.json() == sample


def test_watcher_metrics_endpoint_prometheus(client, monkeypatch):
    monkeypatch.setattr(
        "api.ingestion.watcher_metrics.get_watcher_metrics_snapshot",
        lambda settings: {},
    )
    monkeypatch.setattr(
        "api.ingestion.watcher_metrics.format_metrics_for_prometheus",
        lambda metrics: "watcher_documents_processed_total 0\n",
    )

    response = client.get("/metrics/watcher", params={"format": "prometheus"})
    assert response.status_code == 200
    assert "watcher_documents_processed_total" in response.text
