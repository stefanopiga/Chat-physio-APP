from __future__ import annotations

from collections import Counter, deque
from threading import Lock
from typing import Any, Dict, List, Optional

from api.config import Settings, get_settings
from api.knowledge_base.classification_cache import (
    ClassificationCache,
    get_classification_cache,
)


def _percentile(values: List[float], percentile: float) -> Optional[float]:
    """Return percentile using linear interpolation (1-100 scale)."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    rank = (len(ordered) - 1) * (percentile / 100.0)
    low = int(rank)
    high = low + 1
    if high >= len(ordered):
        return round(ordered[-1], 3)
    weight_high = rank - low
    interpolated = ordered[low] * (1 - weight_high) + ordered[high] * weight_high
    return round(interpolated, 3)


class WatcherMetrics:
    """In-memory metrics aggregator for watcher observability (AC7)."""

    def __init__(self, max_samples: int = 2000) -> None:
        self._lock = Lock()
        self._latencies: deque[float] = deque(maxlen=max_samples)
        self._classification_success = 0
        self._classification_failure = 0
        self._classification_skipped = 0
        self._fallback_count = 0
        self._strategy_counts: Counter[str] = Counter()
        self._documents_processed = 0

    def reset(self) -> None:
        with self._lock:
            self._latencies.clear()
            self._classification_success = 0
            self._classification_failure = 0
            self._classification_skipped = 0
            self._fallback_count = 0
            self._strategy_counts.clear()
            self._documents_processed = 0

    def record_document(self) -> None:
        with self._lock:
            self._documents_processed += 1

    def record_classification(self, outcome: str, latency_ms: Optional[float]) -> None:
        with self._lock:
            if outcome == "success":
                self._classification_success += 1
            elif outcome == "failure":
                self._classification_failure += 1
            elif outcome == "skipped":
                self._classification_skipped += 1

            if latency_ms is not None:
                self._latencies.append(latency_ms)

    def record_strategy(self, strategy_name: str, is_fallback: bool) -> None:
        with self._lock:
            self._strategy_counts[strategy_name] += 1
            if is_fallback:
                self._fallback_count += 1

    def snapshot(
        self,
        cache_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            latencies = list(self._latencies)
            success = self._classification_success
            failure = self._classification_failure
            skipped = self._classification_skipped
            fallback = self._fallback_count
            strategy_counts = dict(self._strategy_counts)
            documents = self._documents_processed

        attempts = success + failure
        classification_ratios: Dict[str, Any] = {
            "success": success,
            "failure": failure,
            "skipped": skipped,
            "success_ratio": round(success / attempts, 4) if attempts else None,
            "failure_ratio": round(failure / attempts, 4) if attempts else None,
        }

        fallback_ratio = round(fallback / documents, 4) if documents else None
        strategy_distribution: Dict[str, Any] = {
            "counts": strategy_counts,
            "ratio": {
                key: round(count / documents, 4) if documents else 0.0
                for key, count in strategy_counts.items()
            },
        }

        latency_metrics = {
            "count": len(latencies),
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
            "p99": _percentile(latencies, 99),
        }

        return {
            "documents_processed": documents,
            "classification": classification_ratios,
            "classification_latency_ms": latency_metrics,
            "fallback": {"count": fallback, "ratio": fallback_ratio},
            "strategy_distribution": strategy_distribution,
            "classification_cache": cache_stats or {},
        }


_WATCHER_METRICS = WatcherMetrics()


def get_metrics() -> WatcherMetrics:
    """Return global watcher metrics collector."""
    return _WATCHER_METRICS


def reset_watcher_metrics() -> None:
    """Utility used in tests to reset the in-memory metrics snapshot."""
    _WATCHER_METRICS.reset()


def get_watcher_metrics_snapshot(settings: Optional[Settings] = None) -> Dict[str, Any]:
    """Expose metrics snapshot for monitoring/telemetry collectors."""
    resolved_settings = settings or get_settings()
    cache = get_classification_cache(resolved_settings)
    cache_stats = cache.get_stats() if isinstance(cache, ClassificationCache) else {}
    return _WATCHER_METRICS.snapshot(cache_stats)


def format_metrics_for_prometheus(metrics: Dict[str, Any]) -> str:
    """Serialize watcher metrics using Prometheus' text exposition format."""
    documents = metrics.get("documents_processed") or 0
    classification = metrics.get("classification") or {}
    fallback = metrics.get("fallback") or {}
    latency = metrics.get("classification_latency_ms") or {}
    distribution = (metrics.get("strategy_distribution") or {}).get("counts", {})
    cache = metrics.get("classification_cache") or {}

    lines: List[str] = []

    lines.append("# HELP watcher_documents_processed_total Numero totale documenti elaborati dal watcher")
    lines.append("# TYPE watcher_documents_processed_total counter")
    lines.append(f"watcher_documents_processed_total {documents}")

    for key in ("success", "failure", "skipped"):
        value = classification.get(key) or 0
        metric_name = f"watcher_classification_{key}_total"
        lines.append(f"# TYPE {metric_name} counter")
        lines.append(f"{metric_name} {value}")

    for ratio_key in ("success_ratio", "failure_ratio"):
        value = classification.get(ratio_key)
        metric_name = f"watcher_{ratio_key}"
        if value is None:
            value = 0
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {value}")

    fallback_count = fallback.get("count") or 0
    fallback_ratio = fallback.get("ratio")
    if fallback_ratio is None:
        fallback_ratio = 0
    lines.append("# TYPE watcher_fallback_total counter")
    lines.append(f"watcher_fallback_total {fallback_count}")
    lines.append("# TYPE watcher_fallback_ratio gauge")
    lines.append(f"watcher_fallback_ratio {fallback_ratio}")

    for percentile in ("p50", "p95", "p99"):
        value = latency.get(percentile)
        if value is None:
            value = 0
        metric_name = f"watcher_classification_latency_ms_{percentile}"
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {value}")

    strategy_counts = distribution or {}
    lines.append("# TYPE watcher_strategy_count counter")
    for strategy, value in sorted(strategy_counts.items()):
        lines.append(f'watcher_strategy_count{{strategy="{strategy}"}} {value}')

    strategy_ratio = (metrics.get("strategy_distribution") or {}).get("ratio", {})
    lines.append("# TYPE watcher_strategy_ratio gauge")
    for strategy, value in sorted(strategy_ratio.items()):
        lines.append(f'watcher_strategy_ratio{{strategy="{strategy}"}} {value}')

    hit_rate = cache.get("hit_rate")
    if hit_rate is None:
        hit_rate = 0
    lines.append("# TYPE watcher_classification_cache_hit_rate gauge")
    lines.append(f"watcher_classification_cache_hit_rate {hit_rate}")

    return "\n".join(lines) + "\n"


__all__ = [
    "WatcherMetrics",
    "get_metrics",
    "get_watcher_metrics_snapshot",
    "reset_watcher_metrics",
    "format_metrics_for_prometheus",
]
