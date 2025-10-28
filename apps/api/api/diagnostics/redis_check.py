from __future__ import annotations

import logging
import time
from typing import Any, Dict

try:
    import redis  # type: ignore
    from redis.exceptions import RedisError  # type: ignore
except Exception:  # pragma: no cover - redis optional in some environments
    redis = None  # type: ignore

    class RedisError(Exception):  # type: ignore
        """Fallback RedisError when redis package missing."""

from api.config import Settings
from api.knowledge_base.classification_cache import (
    get_classification_cache,
    resolve_cache_url,
)

logger = logging.getLogger("api")


def check_redis_health(settings: Settings) -> Dict[str, Any]:
    """
    Perform a lightweight Redis health check capped at 1 second.
    """
    if not settings.classification_cache_enabled:
        logger.info(
            {
                "event": "redis_health_skipped",
                "reason": "classification_cache_disabled",
            }
        )
        return {
            "enabled": False,
            "healthy": True,
            "latency_ms": None,
            "redis_url": None,
        }

    if redis is None:
        logger.warning(
            {
                "event": "redis_health_unavailable",
                "error": "redis_library_missing",
            }
        )
        return {
            "enabled": True,
            "healthy": False,
            "latency_ms": None,
            "redis_url": None,
        }

    cache = get_classification_cache(settings)
    client = getattr(cache, "_redis", None)
    cache_url = resolve_cache_url(settings)
    if client is None:
        logger.warning(
            {
                "event": "redis_health_failed",
                "error": "redis_client_unavailable",
                "redis_url": cache_url,
            }
        )
        return {
            "enabled": True,
            "healthy": False,
            "latency_ms": None,
            "redis_url": cache_url,
        }

    started = time.perf_counter()
    try:
        client.ping()
    except RedisError as exc:
        logger.warning(
            {
                "event": "redis_health_failed",
                "error": str(exc),
                "redis_url": cache_url,
            }
        )
        return {
            "enabled": True,
            "healthy": False,
            "latency_ms": None,
            "redis_url": cache_url,
        }

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        {
            "event": "redis_health_ok",
            "latency_ms": latency_ms,
            "redis_url": cache_url,
        }
    )
    return {
        "enabled": True,
        "healthy": True,
        "latency_ms": latency_ms,
        "redis_url": cache_url,
    }


__all__ = ["check_redis_health"]
