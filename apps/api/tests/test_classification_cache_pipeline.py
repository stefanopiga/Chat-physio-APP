from api.ingestion.models import (
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)
from api.knowledge_base import classifier
from api.knowledge_base.classification_cache import ClassificationCache
from tests.utils import InMemoryRedis


class DummyChain:
    def __init__(self, result: EnhancedClassificationOutput) -> None:
        self.result = result
        self.invocations = 0

    def invoke(self, *_args, **_kwargs) -> EnhancedClassificationOutput:
        self.invocations += 1
        return self.result


def _build_result() -> EnhancedClassificationOutput:
    return EnhancedClassificationOutput(
        domain=ContentDomain.FISIOTERAPIA_CLINICA,
        structure_type=DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO,
        confidence=0.88,
        reasoning="Pipeline test output",
        detected_features={"has_images": False, "has_tables": False},
    )


def _install_chain(monkeypatch, cache: ClassificationCache, chain: DummyChain) -> None:
    class DummyParser:
        def __init__(self, *args, **kwargs):
            pass

        def get_format_instructions(self) -> str:
            return "<<FORMAT>>"

    class DummyPrompt:
        def __init__(self, *args, **kwargs):
            pass

        def __or__(self, _other):
            return DummyPipeline()

    class DummyPipeline:
        def __or__(self, _parser):
            return chain

    monkeypatch.setattr(classifier, "PydanticOutputParser", DummyParser)
    monkeypatch.setattr(classifier, "PromptTemplate", DummyPrompt)
    monkeypatch.setattr(classifier, "_get_llm", lambda: object())
    monkeypatch.setattr(
        classifier,
        "get_classification_cache",
        lambda: cache,
    )


def test_classification_pipeline_caches_result(monkeypatch) -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=300)
    chain = DummyChain(_build_result())
    _install_chain(monkeypatch, cache, chain)

    first = classifier.classify_content_enhanced("document text", {"images_count": 1})
    second = classifier.classify_content_enhanced("document text", {"images_count": 1})

    assert chain.invocations == 1
    assert first.detected_features["has_images"] is True
    assert second.detected_features["has_images"] is True

    stats = cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_classification_pipeline_respects_feature_flag(monkeypatch) -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=False, ttl=300)
    chain = DummyChain(_build_result())
    _install_chain(monkeypatch, cache, chain)

    classifier.classify_content_enhanced("body", {"tables_count": 2})
    classifier.classify_content_enhanced("body", {"tables_count": 2})

    assert chain.invocations == 2
    stats = cache.get_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


def test_classification_pipeline_miss_when_metadata_differs(monkeypatch) -> None:
    cache = ClassificationCache(redis_client=InMemoryRedis(), enabled=True, ttl=300)
    chain = DummyChain(_build_result())
    _install_chain(monkeypatch, cache, chain)

    classifier.classify_content_enhanced("doc text", {"tables_count": 0})
    classifier.classify_content_enhanced("doc text", {"tables_count": 1})

    assert chain.invocations == 2
