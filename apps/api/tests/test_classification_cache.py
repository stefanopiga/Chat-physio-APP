import time

import pytest

from api.ingestion.models import (
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)
from api.knowledge_base import classification_cache as cache_module
from api.knowledge_base.classification_cache import (
    ClassificationCache,
    get_classification_cache,
    reset_classification_cache,
)
from tests.utils import InMemoryRedis


def _build_output() -> EnhancedClassificationOutput:
    return EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=0.92,
        reasoning="Unit test classification output",
        detected_features={"has_images": False},
    )


def test_cache_store_and_retrieve_hit_rate() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)

    assert cache.get("sample", {}) is None
    cache.set("sample", {}, _build_output())
    cached = cache.get("sample", {})

    assert isinstance(cached, EnhancedClassificationOutput)
    assert cached.domain == ContentDomain.ANATOMIA

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate"] == 0.5


def test_cache_ttl_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=1)
    cache.set("expire", {}, _build_output())
    assert cache.get("expire", {}) is not None

    baseline = time.time()
    monkeypatch.setattr("time.time", lambda: baseline + 5)

    expired = cache.get("expire", {})
    assert expired is None


def test_cache_disabled_noops() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=False, ttl=60)
    cache.set("doc", {}, _build_output())
    cached = cache.get("doc", {})
    stats = cache.get_stats()

    assert cached is None
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] is None


def test_delete_by_digest_behaviour() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)
    cache.set("doc", {"source": "test"}, _build_output())

    key, digest = cache._generate_key("doc", {"source": "test"})  # pylint: disable=protected-access

    assert cache.delete_by_digest(digest) is True
    assert cache.delete_by_digest(digest) is False
    assert cache.get("doc", {"source": "test"}) is None


def test_latency_stats_collection() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)
    cache.record_latency(10, cached=True)
    cache.record_latency(20, cached=True)
    cache.record_latency(500, cached=False)

    stats = cache.get_stats()
    assert stats["latency_ms"]["hit"]["count"] == 2
    assert stats["latency_ms"]["hit"]["p50"] == 15.0
    assert stats["latency_ms"]["miss"]["p95"] == 500.0


def test_cache_hash_determinism() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)
    key_a, digest_a = cache._generate_key("doc", {"alpha": 1, "beta": 2})  # pylint: disable=protected-access
    key_b, digest_b = cache._generate_key("doc", {"beta": 2, "alpha": 1})  # pylint: disable=protected-access
    key_c, digest_c = cache._generate_key("doc", {"alpha": 1, "beta": 3})  # pylint: disable=protected-access

    assert key_a == key_b
    assert digest_a == digest_b
    assert digest_c != digest_a


def test_cache_clear_flushes_all_entries() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)
    cache.set("doc", {}, _build_output())
    cache.set("doc", {"meta": "x"}, _build_output())

    removed = cache.clear()
    assert removed == 2
    assert cache.get("doc", {}) is None


def test_cache_handles_missing_redis_client() -> None:
    cache = ClassificationCache(redis_client=None, enabled=True, ttl=60)
    cache.set("doc", {}, _build_output())
    assert cache.get("doc", {}) is None
    assert cache.delete_by_digest("nonexistent") is False
    assert cache.clear() == 0


class BrokenRedis:
    def get(self, key):  # pylint: disable=unused-argument
        raise cache_module.RedisError("boom")

    def setex(self, *args, **kwargs):  # pylint: disable=unused-argument
        raise cache_module.RedisError("boom")

    def delete(self, *args, **kwargs):  # pylint: disable=unused-argument
        raise cache_module.RedisError("boom")


def test_cache_gracefully_handles_redis_errors() -> None:
    cache = ClassificationCache(redis_client=BrokenRedis(), enabled=True, ttl=60)
    assert cache.get("doc", {}) is None
    cache.set("doc", {}, _build_output())
    assert cache.delete_by_digest("abc") is False
    assert cache.clear() == 0
    stats = cache.get_stats()
    assert stats["errors"] > 0


def test_get_classification_cache_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_classification_cache()
    monkeypatch.setenv("CLASSIFICATION_CACHE_ENABLED", "false")
    cache = get_classification_cache()
    assert cache.enabled is False
    reset_classification_cache()
    monkeypatch.delenv("CLASSIFICATION_CACHE_ENABLED")


def test_metadata_variation_changes_digest() -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=60)
    text = "doc body"
    _, digest1 = cache._generate_key(text, {"tables_count": 0})  # pylint: disable=protected-access
    _, digest2 = cache._generate_key(text, {"tables_count": 1})  # pylint: disable=protected-access
    assert digest1 != digest2
