import json
import sys
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from api.config import Settings
from api.ingestion import watcher
from api.ingestion.chunk_router import CONFIDENZA_SOGLIA_FALLBACK
from api.ingestion.config import IngestionConfig
from api.ingestion.models import (
    ClassificazioneOutput,
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)


def _base_settings(**overrides: Any) -> Settings:
    data: Dict[str, Any] = {
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "service-key",
        "supabase_jwt_secret": "jwt-secret",
        "openai_api_key": "sk-test",
        "environment": "development",
        "debug": True,
    }
    data.update(overrides)
    return Settings.model_validate(data)


class _DummyCache:
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.enabled = True

    def get_stats(self) -> Dict[str, int]:
        return {"hits": self.hits, "misses": self.misses}

    def record_latency(self, latency_ms: float, cached: bool) -> None:
        if cached:
            self.hits += 1
        else:
            self.misses += 1


class _DummyMetrics:
    def __init__(self) -> None:
        self.calls: Dict[str, list[Any]] = {
            "record_document": [],
            "record_classification": [],
            "record_strategy": [],
        }

    def record_document(self) -> None:
        self.calls["record_document"].append(True)

    def record_classification(
        self, outcome: str, latency_ms: Optional[float]
    ) -> None:
        self.calls["record_classification"].append((outcome, latency_ms))

    def record_strategy(self, strategy: str, fallback: bool) -> None:
        self.calls["record_strategy"].append((strategy, fallback))


@pytest.fixture()
def stub_metrics(monkeypatch: pytest.MonkeyPatch) -> _DummyMetrics:
    metrics = _DummyMetrics()
    monkeypatch.setattr(watcher, "METRICS", metrics)
    return metrics


@pytest.fixture()
def stub_cache(monkeypatch: pytest.MonkeyPatch) -> _DummyCache:
    cache = _DummyCache()
    monkeypatch.setattr(
        watcher,
        "get_classification_cache",
        lambda settings: cache,
    )
    return cache


@pytest.fixture(autouse=True)
def stub_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        watcher,
        "check_redis_health",
        lambda settings: {"enabled": True, "healthy": True},
    )


@pytest.fixture(autouse=True)
def stub_metrics_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        watcher,
        "get_watcher_metrics_snapshot",
        lambda settings: {"documents_processed": 1},
    )


def test_compute_file_hash_is_stable(tmp_path: Path) -> None:
    target = tmp_path / "document.txt"
    target.write_text("content", encoding="utf-8")
    first = watcher.compute_file_hash(target)
    second = watcher.compute_file_hash(target)
    assert first == second


def test_classify_with_timeout_identifies_cache_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=0.9,
        reasoning="sufficient reasoning",
        detected_features={},
    )

    class DummyFuture:
        def result(self, timeout: Optional[int] = None) -> Any:
            return result

    class DummyExecutor:
        def submit(self, func, *args, **kwargs):
            return DummyFuture()

    class CacheWithHitGrowth(_DummyCache):
        def __init__(self) -> None:
            super().__init__()
            self._call = 0

        def get_stats(self) -> Dict[str, int]:
            self._call += 1
            if self._call == 1:
                return {"hits": 0, "misses": 0}
            return {"hits": 1, "misses": 0}

    cache = CacheWithHitGrowth()

    monkeypatch.setattr(watcher, "_CLASSIFICATION_EXECUTOR", DummyExecutor())
    monkeypatch.setattr(
        watcher,
        "classify_content_enhanced",
        lambda *args, **kwargs: result,
    )

    _, meta = watcher._classify_with_timeout("text", {}, 5, cache)
    assert meta["source"] == "cache"
    assert meta["cache"]["hits"] >= 1


def test_classify_with_timeout_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyFuture:
        def __init__(self) -> None:
            self.cancelled = False

        def result(self, timeout: Optional[int] = None) -> Any:
            raise FutureTimeoutError()

        def cancel(self) -> None:
            self.cancelled = True

    class DummyExecutor:
        def submit(self, func, *args, **kwargs):
            self.future = DummyFuture()
            return self.future

    executor = DummyExecutor()
    monkeypatch.setattr(watcher, "_CLASSIFICATION_EXECUTOR", executor)

    with pytest.raises(watcher.ClassificationTimeoutError):
        watcher._classify_with_timeout("text", {}, 1, _DummyCache())

    assert executor.future.cancelled is True


def _prepare_watcher_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    extracted_text: str,
    classification_result: Optional[EnhancedClassificationOutput] = None,
    classification_meta: Optional[Dict[str, Any]] = None,
    router_strategy: str = "dummy_strategy",
    router_parameters: Optional[Dict[str, Any]] = None,
    router_chunks: Optional[list[str]] = None,
    classification_exception: Optional[Exception] = None,
    skip_classification: bool = False,
) -> tuple[IngestionConfig, dict[str, str], Path]:
    watch_dir = tmp_path / "watch"
    temp_dir = tmp_path / "temp"
    watch_dir.mkdir()
    temp_dir.mkdir()

    target_file = watch_dir / "doc.txt"
    target_file.write_text("original content", encoding="utf-8")

    inventory: dict[str, str] = {}
    cfg = IngestionConfig(watch_dir=watch_dir, temp_dir=temp_dir)

    class DummyExtractor:
        def extract(self, path: Path) -> Dict[str, Any]:
            assert path == target_file
            payload: Dict[str, Any] = {"text": extracted_text}
            payload["metadata"] = {"images_count": 1, "tables_count": 0}
            return payload

    class DummyRouter:
        def route(self, content: str, classification: Optional[ClassificazioneOutput]):
            class DummyRouting:
                chunks = router_chunks or ["chunk-one"]
                strategy_name = router_strategy
                parameters = router_parameters or {"window": 200}

            return DummyRouting()

    monkeypatch.setattr(watcher, "_DOCUMENT_EXTRACTOR", DummyExtractor())
    monkeypatch.setattr(watcher, "ChunkRouter", DummyRouter)

    if classification_exception:

        def raise_exc(*args, **kwargs):
            raise classification_exception

        monkeypatch.setattr(watcher, "_classify_with_timeout", raise_exc)
    elif skip_classification:
        monkeypatch.setattr(
            watcher,
            "_classify_with_timeout",
            lambda *args, **kwargs: (_DummyCache(), {}),
        )
    elif classification_result:
        meta = classification_meta or {"source": "llm"}
        monkeypatch.setattr(
            watcher,
            "_classify_with_timeout",
            lambda *args, **kwargs: (classification_result, meta),
        )
    else:
        raise AssertionError("classification_result required unless skip_classification is True")

    return cfg, inventory, target_file


@pytest.mark.asyncio
async def test_scan_once_successful_flow(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stub_metrics: _DummyMetrics,
    stub_cache: _DummyCache,
) -> None:
    classification = EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=0.87,
        reasoning="deterministic reasoning",
        detected_features={"has_images": True},
    )
    cfg, inventory, target = _prepare_watcher_environment(
        monkeypatch,
        tmp_path,
        extracted_text="Processed content",
        classification_result=classification,
        classification_meta={"source": "llm"},
    )

    results = await watcher.scan_once(cfg, inventory, _base_settings(), conn=None)

    assert len(results) == 1
    doc = results[0]
    assert doc.status == "chunked"  # No DB conn → stays "chunked"
    assert doc.chunking_strategy == "dummy_strategy"
    assert doc.metadata["classification"]["status"] == "success"
    assert inventory[str(target)] == doc.file_hash
    assert stub_metrics.calls["record_document"]
    assert stub_metrics.calls["record_classification"][-1][0] == "success"


@pytest.mark.asyncio
async def test_scan_once_handles_feature_flag_with_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stub_metrics: _DummyMetrics,
) -> None:
    cfg, inventory, _ = _prepare_watcher_environment(
        monkeypatch,
        tmp_path,
        extracted_text="classified content",
        router_strategy="fallback::recursive",
        skip_classification=True,
    )

    settings = _base_settings()
    settings.watcher_enable_classification = False

    results = await watcher.scan_once(cfg, inventory, settings, conn=None)

    doc = results[0]
    assert doc.metadata["classification"]["status"] == "skipped"
    assert doc.metadata["routing"]["fallback"] is True
    assert doc.metadata["routing"]["fallback_reason"] == "feature_flag_disabled"
    assert stub_metrics.calls["record_classification"][-1][0] == "skipped"


@pytest.mark.asyncio
async def test_scan_once_handles_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stub_metrics: _DummyMetrics,
    stub_cache: _DummyCache,
) -> None:
    cfg, inventory, _ = _prepare_watcher_environment(
        monkeypatch,
        tmp_path,
        extracted_text="content for timeout",
        classification_result=None,
        classification_exception=watcher.ClassificationTimeoutError(),
    )

    results = await watcher.scan_once(cfg, inventory, _base_settings(), conn=None)
    doc = results[0]
    assert doc.metadata["classification"]["status"] == "timeout"
    assert doc.metadata["routing"]["fallback_reason"] == "classification_timeout"
    assert stub_metrics.calls["record_classification"][-1][0] == "failure"


@pytest.mark.asyncio
async def test_scan_once_handles_empty_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg, inventory, _ = _prepare_watcher_environment(
        monkeypatch,
        tmp_path,
        extracted_text="",
        router_strategy="fallback::empty",
        skip_classification=True,
    )

    results = await watcher.scan_once(cfg, inventory, _base_settings(), conn=None)
    doc = results[0]
    classification = doc.metadata["classification"]
    assert classification["status"] == "skipped"
    assert classification["reason"] == "empty_content"
    assert doc.metadata["routing"]["fallback"] is True
    assert doc.metadata["routing"]["fallback_reason"] == "empty_content"


@pytest.mark.asyncio
async def test_scan_once_records_chunking_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    classification = EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=0.9,
        reasoning="valid reasoning text",
        detected_features={},
    )
    cfg, inventory, _ = _prepare_watcher_environment(
        monkeypatch,
        tmp_path,
        extracted_text="content",
        classification_result=classification,
    )

    def failing_route(*args, **kwargs):
        raise RuntimeError("chunking failed")

    class FailingRouter:
        def route(self, *args, **kwargs):
            raise RuntimeError("chunking failed")

    monkeypatch.setattr(watcher, "ChunkRouter", FailingRouter)

    results = await watcher.scan_once(cfg, inventory, _base_settings(), conn=None)
    doc = results[0]
    assert doc.status == "error"
    assert doc.error == "chunking failed"


def test_run_diag_handles_missing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from api.ingestion import run_diag

    settings = _base_settings()

    monkeypatch.setattr(run_diag, "load_dotenv", lambda override=True: None)
    monkeypatch.setattr(run_diag, "get_settings", lambda: settings)
    monkeypatch.setattr(run_diag, "IngestionConfig", IngestionConfig)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_diag.py", "--file", str(tmp_path / "missing.txt")],
    )

    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 1


def _prepare_run_diag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    text: str,
    settings: Optional[Settings] = None,
    classification: Optional[EnhancedClassificationOutput] = None,
    classification_meta: Optional[Dict[str, Any]] = None,
    classification_exception: Optional[Exception] = None,
    router_strategy: str = "dummy_strategy",
    router_chunks: Optional[list[str]] = None,
) -> Path:
    from api.ingestion import run_diag

    settings = settings or _base_settings()
    monkeypatch.setattr(run_diag, "load_dotenv", lambda override=True: None)
    monkeypatch.setattr(run_diag, "get_settings", lambda: settings)

    watch_dir = tmp_path / "watch"
    temp_dir = tmp_path / "temp"
    watch_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)

    settings.ingestion_watch_dir = str(watch_dir)
    settings.ingestion_temp_dir = str(temp_dir)
    monkeypatch.setattr(run_diag, "IngestionConfig", IngestionConfig)

    target = tmp_path / "doc.txt"
    target.write_text("original content", encoding="utf-8")

    class DummyExtractor:
        def extract(self, path: Path) -> Dict[str, Any]:
            return {
                "text": text,
                "metadata": {"images_count": 0, "tables_count": 0},
            }

    monkeypatch.setattr(run_diag, "DocumentExtractor", lambda: DummyExtractor())

    class DummyRouter:
        def route(self, *_args, **_kwargs):
            class DummyRouting:
                chunks = router_chunks or ["chunk"]
                strategy_name = router_strategy
                parameters = {"chunk_size": 1000}

            return DummyRouting()

    monkeypatch.setattr(run_diag, "ChunkRouter", DummyRouter)
    monkeypatch.setattr(
        run_diag,
        "check_redis_health",
        lambda _settings: {"enabled": True, "healthy": True},
    )
    monkeypatch.setattr(
        run_diag,
        "get_classification_cache",
        lambda _settings: object(),
    )
    monkeypatch.setattr(
        run_diag,
        "get_watcher_metrics_snapshot",
        lambda _settings: {"documents_processed": 1},
    )

    if classification_exception:

        def raise_exc(*args, **kwargs):
            raise classification_exception

        monkeypatch.setattr(run_diag, "_classify_with_timeout", raise_exc)
    elif classification:
        monkeypatch.setattr(
            run_diag,
            "_classify_with_timeout",
            lambda *args, **kwargs: (classification, classification_meta or {"source": "llm"}),
        )
    else:
        monkeypatch.setattr(
            run_diag,
            "_classify_with_timeout",
            lambda *args, **kwargs: (_DummyCache(), {}),
        )

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_diag.py", "--file", str(target)],
    )

    return target


def test_run_diag_skips_empty_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    from api.ingestion import run_diag

    _prepare_run_diag(monkeypatch, tmp_path, text="")
    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Diagnostic report saved" in output

    diag_dir = (tmp_path / "temp" / "diag")
    reports = list(diag_dir.glob("*.json"))
    assert reports, "diagnostic report expected"
    data = json.loads(reports[0].read_text(encoding="utf-8"))
    assert data["classification"]["reason"] == "empty_content"


def test_run_diag_skips_feature_flag_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    from api.ingestion import run_diag

    settings = _base_settings(watcher_enable_classification=False)
    _prepare_run_diag(monkeypatch, tmp_path, text="content", settings=settings)

    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Classification completed" not in output


def test_run_diag_handles_classification_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    from api.ingestion import run_diag

    _prepare_run_diag(
        monkeypatch,
        tmp_path,
        text="content",
        classification_exception=watcher.ClassificationTimeoutError(),
    )

    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 2
    output = capsys.readouterr().out
    assert "Classification timed out" in output


def test_run_diag_reports_fallback_reason_for_low_confidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    from api.ingestion import run_diag

    classification = EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=CONFIDENZA_SOGLIA_FALLBACK / 2,
        reasoning="low confidence",
        detected_features={},
    )
    _prepare_run_diag(
        monkeypatch,
        tmp_path,
        text="content",
        classification=classification,
        router_strategy="fallback::strategy",
    )

    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "Fallback reason" in output

    diag_dir = tmp_path / "temp" / "diag"
    reports = list(diag_dir.glob("*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["routing"]["fallback_reason"] == "low_confidence"
