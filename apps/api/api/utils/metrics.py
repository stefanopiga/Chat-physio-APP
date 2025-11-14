"""
Metrics collection utilities (Story 9.1).

Stub implementation per metrics collection. In produzione sostituire con
Prometheus client, StatsD, o DataDog StatsD client.

Story 9.1 AC7: Metrics per DB writes, cache performance, session tracking,
backpressure, circuit breaker, outbox queue.

Usage:
    from ..utils.metrics import metrics
    
    metrics.increment("db_writes_succeeded")
    metrics.histogram("db_write_latency_ms", 45.2)
    metrics.gauge("active_sessions_count", 12)
"""
import logging
from typing import Dict, List

logger = logging.getLogger("metrics")


class MetricsCollector:
    """
    In-memory metrics collector (stub implementation).
    
    Story 9.1 AC7: Collects counters, histograms, gauges per monitoring.
    
    Features:
    - Counters: Incremento monotono (es. db_writes_succeeded)
    - Histograms: Distribuzioni valori (es. db_write_latency_ms)
    - Gauges: Valori point-in-time (es. active_sessions_count)
    
    Production:
        Replace with Prometheus client:
        from prometheus_client import Counter, Histogram, Gauge
    """
    
    def __init__(self):
        """Initialize metrics storage."""
        self._counters: Dict[str, int] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
    
    def increment(self, name: str, value: int = 1) -> None:
        """
        Increment counter metric.
        
        Args:
            name: Metric name (es. 'db_writes_succeeded')
            value: Increment amount (default 1)
        """
        current = self._counters.get(name, 0)
        self._counters[name] = current + value
        
        logger.debug({
            "event": "metric_counter_increment",
            "metric": name,
            "value": value,
            "total": self._counters[name],
        })
    
    def histogram(self, name: str, value: float) -> None:
        """
        Record histogram metric (distribution).
        
        Args:
            name: Metric name (es. 'db_write_latency_ms')
            value: Observed value
        """
        if name not in self._histograms:
            self._histograms[name] = []
        
        self._histograms[name].append(value)
        
        # Keep only last 1000 samples per metric (memory bound)
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]
        
        logger.debug({
            "event": "metric_histogram_record",
            "metric": name,
            "value": value,
        })
    
    def gauge(self, name: str, value: float) -> None:
        """
        Set gauge metric (point-in-time value).
        
        Args:
            name: Metric name (es. 'active_sessions_count')
            value: Current value
        """
        self._gauges[name] = value
        
        logger.debug({
            "event": "metric_gauge_set",
            "metric": name,
            "value": value,
        })
    
    def get_counter(self, name: str) -> int:
        """
        Get counter value.
        
        Args:
            name: Metric name
        
        Returns:
            Current counter value (0 if not exists)
        """
        return self._counters.get(name, 0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """
        Get histogram statistics (p50, p95, p99).
        
        Args:
            name: Metric name
        
        Returns:
            Dict con min, max, p50, p95, p99, count
        """
        samples = self._histograms.get(name, [])
        
        if not samples:
            return {
                "count": 0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        
        sorted_samples = sorted(samples)
        count = len(sorted_samples)
        
        def percentile(p: float) -> float:
            """Calculate percentile."""
            k = (count - 1) * p
            f = int(k)
            c = f + 1
            if c >= count:
                return sorted_samples[-1]
            d0 = sorted_samples[f] * (c - k)
            d1 = sorted_samples[c] * (k - f)
            return d0 + d1
        
        return {
            "count": count,
            "min": sorted_samples[0],
            "max": sorted_samples[-1],
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        }
    
    def get_gauge(self, name: str) -> float:
        """
        Get gauge value.
        
        Args:
            name: Metric name
        
        Returns:
            Current gauge value (0.0 if not exists)
        """
        return self._gauges.get(name, 0.0)
    
    def reset(self) -> None:
        """Reset all metrics (per testing)."""
        self._counters.clear()
        self._histograms.clear()
        self._gauges.clear()
        logger.info({"event": "metrics_reset"})


# Global singleton instance
metrics = MetricsCollector()

