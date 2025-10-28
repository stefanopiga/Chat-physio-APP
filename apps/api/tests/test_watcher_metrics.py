from types import SimpleNamespace

import pytest

from api.ingestion.watcher_metrics import (
    WatcherMetrics,
    _percentile,
    format_metrics_for_prometheus,
    get_metrics,
    get_watcher_metrics_snapshot,
    reset_watcher_metrics,
)
from api.knowledge_base.classification_cache import ClassificationCache


@pytest.fixture(autouse=True)
def _reset_global_metrics():
    reset_watcher_metrics()
    yield
    reset_watcher_metrics()


def test_percentile_helper_handles_edge_cases():
    assert _percentile([], 50) is None
    assert _percentile([42.0], 95) == 42.0
    assert _percentile([10.0, 30.0, 50.0], 50) == 30.0
    assert _percentile([10.0, 30.0, 50.0], 95) == pytest.approx(48.0)
    assert _percentile([10.0, 30.0, 50.0], 99) == pytest.approx(49.6)


def test_watcher_metrics_snapshot_calculates_ratios():
    metrics = WatcherMetrics()
    for _ in range(3):
        metrics.record_document()

    metrics.record_classification("success", 10.0)
    metrics.record_classification("failure", 30.0)
    metrics.record_classification("success", 50.0)
    metrics.record_classification("skipped", None)

    metrics.record_strategy("tabular_structural", False)
    metrics.record_strategy("fallback::recursive_character_800_160", True)

    snapshot = metrics.snapshot({"hits": 3, "misses": 2, "hit_rate": 0.6})

    assert snapshot["documents_processed"] == 3
    assert snapshot["classification"]["success"] == 2
    assert snapshot["classification"]["failure"] == 1
    assert snapshot["classification"]["skipped"] == 1
    assert snapshot["classification"]["success_ratio"] == pytest.approx(2 / 3, rel=1e-3)

    assert snapshot["fallback"]["count"] == 1
    assert snapshot["fallback"]["ratio"] == pytest.approx(1 / 3, rel=1e-3)

    latency = snapshot["classification_latency_ms"]
    assert latency["count"] == 3
    assert latency["p50"] == pytest.approx(30.0)
    assert latency["p95"] == pytest.approx(48.0)
    assert latency["p99"] == pytest.approx(49.6)

    strategy_counts = snapshot["strategy_distribution"]["counts"]
    assert strategy_counts["tabular_structural"] == 1
    assert strategy_counts["fallback::recursive_character_800_160"] == 1


def test_get_watcher_metrics_snapshot_includes_cache_stats(monkeypatch):
    # Populate global metrics object
    metrics = get_metrics()
    metrics.record_document()
    metrics.record_classification("success", 25.0)
    metrics.record_strategy("tabular_structural", False)

    cache = ClassificationCache(redis_client=None, enabled=True, ttl=600)
    for _ in range(5):
        cache._record_hit()  # type: ignore[attr-defined]
    cache._record_miss()  # type: ignore[attr-defined]

    monkeypatch.setattr(
        "api.ingestion.watcher_metrics.get_classification_cache",
        lambda settings=None: cache,
    )

    settings = SimpleNamespace(
        classification_cache_enabled=True,
        classification_cache_ttl_seconds=600,
        classification_cache_redis_url=None,
        celery_broker_url="redis://localhost:6379/0",
    )

    snapshot = get_watcher_metrics_snapshot(settings)

    assert snapshot["classification"]["success"] == 1
    assert snapshot["classification_cache"]["hit_rate"] == pytest.approx(0.8333)


def test_format_metrics_for_prometheus_outputs_expected_lines():
    metrics_dict = {
        "documents_processed": 2,
        "classification": {
            "success": 1,
            "failure": 1,
            "skipped": 0,
            "success_ratio": None,
            "failure_ratio": 0.5,
        },
        "fallback": {"count": 1, "ratio": None},
        "classification_latency_ms": {"p50": 12.3, "p95": None, "p99": 21.7},
        "strategy_distribution": {
            "counts": {"tabular_structural": 2},
            "ratio": {"tabular_structural": 1.0},
        },
        "classification_cache": {"hit_rate": None},
    }

    output = format_metrics_for_prometheus(metrics_dict)

    assert "watcher_documents_processed_total 2" in output
    assert "watcher_classification_success_total 1" in output
    assert "watcher_classification_failure_total 1" in output
    assert "watcher_classification_skipped_total 0" in output
    assert "watcher_success_ratio 0" in output
    assert "watcher_failure_ratio 0.5" in output
    assert "watcher_fallback_total 1" in output
    assert "watcher_fallback_ratio 0" in output
    assert 'watcher_strategy_count{strategy="tabular_structural"} 2' in output
    assert 'watcher_strategy_ratio{strategy="tabular_structural"} 1.0' in output
    assert "watcher_classification_cache_hit_rate 0" in output
