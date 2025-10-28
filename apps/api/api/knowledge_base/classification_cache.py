"""Redis-backed caching layer for enhanced classification results.

Implements deterministic hashing based on document text + metadata to
ensure identical inputs share cached outputs. Provides graceful
degradation when Redis is unavailable, structured logging for cache
events, and rolling metrics for observability.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from collections import deque
from threading import Lock, RLock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

try:
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - library missing in some environments
    redis = None

    class RedisError(Exception):  # type: ignore
        """Fallback exception when redis package is unavailable."""

from ..config import Settings, get_settings
from ..ingestion.models import EnhancedClassificationOutput

logger = logging.getLogger("api")


def _stringify_metadata(value: Any) -> Any:
    """Convert metadata values to JSON-serialisable primitives."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [_stringify_metadata(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _stringify_metadata(v) for k, v in value.items()}
    return str(value)


def _serialise_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    """Serialise metadata deterministically for hashing."""
    if not metadata:
        return ""
    try:
        return json.dumps(metadata, sort_keys=True, separators=(",", ":"))
    except TypeError:
        normalised = _stringify_metadata(metadata)
        return json.dumps(normalised, sort_keys=True, separators=(",", ":"))


def _percentile(values: deque[float], percentile: float) -> Optional[float]:
    """Compute percentile using linear interpolation (1-100 scale)."""
    if not values:
        return None
    data = sorted(values)
    if len(data) == 1:
        return round(data[0], 3)
    rank = (len(data) - 1) * (percentile / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return round(data[int(rank)], 3)
    weight_high = rank - low
    interpolated = data[low] * (1 - weight_high) + data[high] * weight_high
    return round(interpolated, 3)


def resolve_cache_url(settings: Settings) -> str:
    """Determine Redis URL for cache, defaulting to isolated DB 1."""
    if settings.classification_cache_redis_url:
        return settings.classification_cache_redis_url

    broker_url = settings.celery_broker_url or ""
    if broker_url.startswith("redis://"):
        parsed = urlparse(broker_url)
        path = parsed.path.lstrip("/") if parsed.path else ""
        try:
            db = int(path) if path else 0
        except ValueError:
            db = 0
        cache_db = db + 1 if db < 15 else db
        parsed = parsed._replace(path=f"/{cache_db}")
        return urlunparse(parsed)

    return "redis://localhost:6379/1"


class ClassificationCache:
    """Redis caching helper with graceful fallback and metrics."""

    def __init__(
        self,
        redis_client: Optional["redis.Redis"],
        enabled: bool,
        ttl: int,
        namespace: str = "classification:v1",
    ) -> None:
        self._redis = redis_client
        self.enabled = bool(enabled and redis_client)
        self.ttl = ttl if ttl > 0 else 1
        self.namespace = namespace

        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._latency_hits: deque[float] = deque(maxlen=1000)
        self._latency_misses: deque[float] = deque(maxlen=1000)
        self._lock = Lock()

    def _generate_key(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        payload = f"{text}::{_serialise_metadata(metadata)}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{self.namespace}:{digest}", digest

    def _record_hit(self) -> None:
        with self._lock:
            self._hits += 1

    def _record_miss(self) -> None:
        with self._lock:
            self._misses += 1

    def _record_error(self) -> None:
        with self._lock:
            self._errors += 1

    def record_latency(self, duration_ms: float, cached: bool) -> None:
        """Track latency samples for observability."""
        if duration_ms < 0:
            return
        with self._lock:
            if cached:
                self._latency_hits.append(duration_ms)
            else:
                self._latency_misses.append(duration_ms)

    def get(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[EnhancedClassificationOutput]:
        """Fetch cached classification if available."""
        if not self.enabled or not self._redis:
            return None

        key, _ = self._generate_key(text, metadata)
        try:
            cached = self._redis.get(key)
            if cached is None:
                self._record_miss()
                logger.info({"event": "classification_cache_miss", "key": key})
                return None

            if isinstance(cached, bytes):
                cached = cached.decode("utf-8")

            result = EnhancedClassificationOutput.model_validate_json(cached)
            self._record_hit()
            logger.info({"event": "classification_cache_hit", "key": key})
            return result
        except RedisError as exc:  # pragma: no cover - requires Redis failure
            self._record_error()
            logger.warning(
                {
                    "event": "classification_cache_error",
                    "key": key,
                    "error": str(exc),
                }
            )
        except Exception as exc:  # pragma: no cover - parsing errors unexpected
            self._record_error()
            logger.warning(
                {
                    "event": "classification_cache_error",
                    "key": key,
                    "error": str(exc),
                }
            )
        return None

    def set(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]],
        result: EnhancedClassificationOutput,
    ) -> None:
        """Store classification output in cache."""
        if not self.enabled or not self._redis:
            return

        key, _ = self._generate_key(text, metadata)
        try:
            payload = result.model_dump_json()
            self._redis.setex(key, self.ttl, payload)
        except RedisError as exc:  # pragma: no cover - requires Redis failure
            self._record_error()
            logger.warning(
                {
                    "event": "classification_cache_error",
                    "key": key,
                    "error": str(exc),
                }
            )

    def delete_by_digest(self, digest: str) -> bool:
        """Delete cached entry using the digest portion of the key."""
        if not self.enabled or not self._redis:
            return False
        key = f"{self.namespace}:{digest}"
        try:
            removed = self._redis.delete(key)
            logger.info(
                {
                    "event": "classification_cache_delete",
                    "key": key,
                    "removed": bool(removed),
                }
            )
            return bool(removed)
        except RedisError as exc:  # pragma: no cover - requires Redis failure
            self._record_error()
            logger.warning(
                {
                    "event": "classification_cache_error",
                    "key": key,
                    "error": str(exc),
                }
            )
            return False

    def clear(self) -> int:
        """Flush all cached entries for the classification namespace."""
        if not self.enabled or not self._redis:
            return 0

        try:
            pattern = f"{self.namespace}:*"
            keys: List[Any] = []
            if hasattr(self._redis, "scan_iter"):
                keys = list(self._redis.scan_iter(match=pattern))
            elif hasattr(self._redis, "keys"):
                raw_keys = self._redis.keys(pattern)  # type: ignore[attr-defined]
                keys = list(raw_keys) if raw_keys else []

            if not keys:
                return 0

            removed = self._redis.delete(*keys)
            removed_count = int(removed or 0)
            logger.info(
                {
                    "event": "classification_cache_flush",
                    "prefix": self.namespace,
                    "removed": removed_count,
                }
            )
            return removed_count
        except RedisError as exc:  # pragma: no cover - requires Redis failure
            self._record_error()
            logger.warning(
                {
                    "event": "classification_cache_error",
                    "error": str(exc),
                    "prefix": self.namespace,
                }
            )
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregated cache metrics for dashboard export."""
        with self._lock:
            hits = self._hits
            misses = self._misses
            errors = self._errors
            hit_rate = None
            total = hits + misses
            if total:
                hit_rate = round(hits / total, 4)
            latency_hit = list(self._latency_hits)
            latency_miss = list(self._latency_misses)

        stats = {
            "enabled": self.enabled,
            "hits": hits,
            "misses": misses,
            "errors": errors,
            "hit_rate": hit_rate,
            "latency_ms": {
                "hit": {
                    "count": len(latency_hit),
                    "p50": _percentile(deque(latency_hit, maxlen=len(latency_hit)), 50),
                    "p95": _percentile(deque(latency_hit, maxlen=len(latency_hit)), 95),
                },
                "miss": {
                    "count": len(latency_miss),
                    "p50": _percentile(
                        deque(latency_miss, maxlen=len(latency_miss)), 50
                    ),
                    "p95": _percentile(
                        deque(latency_miss, maxlen=len(latency_miss)), 95
                    ),
                },
            },
        }
        return stats


_cache_instance: Optional[ClassificationCache] = None
_cache_lock = RLock()


def get_classification_cache(settings: Optional[Settings] = None) -> ClassificationCache:
    """Return singleton cache instance initialised from settings."""
    global _cache_instance
    if _cache_instance is not None:
        return _cache_instance

    with _cache_lock:
        if _cache_instance is not None:
            return _cache_instance

        if settings is None:
            settings = get_settings()

        redis_client = None
        if settings.classification_cache_enabled and redis is not None:
            cache_url = resolve_cache_url(settings)
            try:
                redis_client = redis.from_url(  # type: ignore[attr-defined]
                    cache_url,
                    decode_responses=False,
                    socket_timeout=1,
                    socket_connect_timeout=1,
                )
                redis_client.ping()
                logger.info(
                    {
                        "event": "classification_cache_ready",
                        "redis_url": cache_url,
                    }
                )
            except Exception as exc:  # pragma: no cover - requires Redis failure
                logger.warning(
                    {
                        "event": "classification_cache_error",
                        "error": f"redis_connection_failed: {exc}",
                        "redis_url": cache_url,
                    }
                )
                redis_client = None

        _cache_instance = ClassificationCache(
            redis_client=redis_client,
            enabled=settings.classification_cache_enabled,
            ttl=settings.classification_cache_ttl_seconds,
        )

    return _cache_instance


def reset_classification_cache() -> None:
    """Reset singleton instance (used in tests)."""
    global _cache_instance
    with _cache_lock:
        _cache_instance = None


__all__ = [
    "ClassificationCache",
    "get_classification_cache",
    "resolve_cache_url",
    "reset_classification_cache",
]
