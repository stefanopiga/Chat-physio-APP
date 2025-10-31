import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.ingestion.config import IngestionConfig
from api.ingestion.models import (
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)
from api.ingestion.watcher import (
    get_watcher_metrics_snapshot,
    reset_watcher_metrics,
    scan_once,
)
from api.knowledge_base.classification_cache import reset_classification_cache


def _make_settings(enable_classification: bool = True, timeout_seconds: float = 1.0):
    return SimpleNamespace(
        watcher_enable_classification=enable_classification,
        classification_timeout_seconds=timeout_seconds,
        classification_cache_enabled=False,
        classification_cache_ttl_seconds=600,
        classification_cache_redis_url=None,
        celery_broker_url="redis://localhost:6379/0",
    )


def _prepare_cfg(tmp_path: Path, content: str) -> IngestionConfig:
    watch = tmp_path / "watch"
    temp = tmp_path / "temp"
    watch.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    (watch / "documento.txt").write_text(content, encoding="utf-8")
    return IngestionConfig(watch_dir=watch, temp_dir=temp)


def _stub_classification(structure: DocumentStructureCategory, confidence: float = 0.9):
    return EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=structure,
        confidence=confidence,
        reasoning="stubbed",
        detected_features={"has_tables": structure == DocumentStructureCategory.DOCUMENTO_TABELLARE},
    )


@pytest.fixture(autouse=True)
def _reset_state():
    reset_watcher_metrics()
    reset_classification_cache()
    yield
    reset_watcher_metrics()
    reset_classification_cache()


@pytest.mark.asyncio
async def test_watcher_routes_tabular_strategy(monkeypatch, tmp_path):
    def fake_classify(text: str, metadata):
        return _stub_classification(DocumentStructureCategory.DOCUMENTO_TABELLARE, confidence=0.92)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", fake_classify)

    cfg = _prepare_cfg(tmp_path, "Tabella 1\n\nCella A | Cella B")
    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    assert len(docs) == 1
    doc = docs[0]

    assert doc.chunking_strategy == "tabular_structural"
    routing = doc.metadata["routing"]
    assert routing["fallback"] is False
    assert routing["fallback_reason"] is None

    classification = doc.metadata["classification"]
    assert classification["status"] == "success"
    assert classification["structure_type"] == DocumentStructureCategory.DOCUMENTO_TABELLARE.value

    metrics = get_watcher_metrics_snapshot(settings)
    assert metrics["classification"]["success"] == 1
    assert metrics["strategy_distribution"]["counts"]["tabular_structural"] == 1


@pytest.mark.asyncio
async def test_watcher_low_confidence_triggers_fallback(monkeypatch, tmp_path):
    def fake_classify(text: str, metadata):
        return _stub_classification(DocumentStructureCategory.DOCUMENTO_TABELLARE, confidence=0.3)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", fake_classify)

    cfg = _prepare_cfg(tmp_path, "Dato 1\n\nDato 2")
    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]

    assert doc.chunking_strategy.startswith("fallback::")
    routing = doc.metadata["routing"]
    assert routing["fallback"] is True
    assert routing["fallback_reason"] == "low_confidence"

    metrics = get_watcher_metrics_snapshot(settings)
    assert metrics["fallback"]["count"] == 1
    assert metrics["classification"]["success"] == 1  # classification succeeded but fell back


@pytest.mark.asyncio
async def test_watcher_timeout_graceful_degradation(monkeypatch, tmp_path):
    def slow_classify(text: str, metadata):
        time.sleep(0.1)
        return _stub_classification(DocumentStructureCategory.TESTO_ACCADEMICO_DENSO, confidence=0.9)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", slow_classify)

    cfg = _prepare_cfg(tmp_path, "Contenuto denso " * 5)
    settings = _make_settings(enable_classification=True, timeout_seconds=0.01)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]

    assert doc.chunking_strategy.startswith("fallback::")
    classification = doc.metadata["classification"]
    assert classification["status"] == "timeout"
    routing = doc.metadata["routing"]
    assert routing["fallback_reason"] == "classification_timeout"

    metrics = get_watcher_metrics_snapshot(settings)
    assert metrics["classification"]["failure"] == 1
    assert metrics["fallback"]["count"] == 1


@pytest.mark.asyncio
async def test_watcher_extracts_docx_metadata(monkeypatch, tmp_path):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_paragraph("Paragrafo iniziale")
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Header"

    watch = tmp_path / "watch"
    temp = tmp_path / "temp"
    watch.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    docx_path = watch / "documento.docx"
    document.save(docx_path)

    def fake_classify(text: str, metadata):
        return _stub_classification(DocumentStructureCategory.TESTO_ACCADEMICO_DENSO, confidence=0.88)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", fake_classify)

    cfg = IngestionConfig(watch_dir=watch, temp_dir=temp)
    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]

    assert doc.metadata["tables_count"] == 1
    assert doc.metadata["images_count"] == 0
    assert doc.metadata["classification"]["status"] == "success"


@pytest.mark.asyncio
async def test_watcher_handles_pdf_input(monkeypatch, tmp_path):
    watch = tmp_path / "watch"
    temp = tmp_path / "temp"
    watch.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    pdf_path = watch / "documento.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%Mock PDF content for tests\n%%EOF")

    extract_calls = []

    def fake_extract(path: Path):
        extract_calls.append(path)
        return {
            "text": "Contenuto PDF di test",
            "metadata": {"images_count": 0, "tables_count": 0},
            "images": [],
            "tables": [],
        }

    monkeypatch.setattr("api.ingestion.watcher._DOCUMENT_EXTRACTOR.extract", fake_extract)

    def fake_classify(text: str, metadata):
        return _stub_classification(DocumentStructureCategory.TESTO_ACCADEMICO_DENSO, confidence=0.91)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", fake_classify)

    cfg = IngestionConfig(watch_dir=watch, temp_dir=temp)
    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]

    assert extract_calls and extract_calls[0].suffix == ".pdf"
    assert doc.metadata["classification"]["status"] == "success"
    assert doc.metadata["routing"]["fallback"] is False
    assert doc.chunking_strategy == "recursive_character_800_160"
    assert doc.metadata["chunks_count"] > 0


@pytest.mark.asyncio
async def test_watcher_handles_extraction_failure(monkeypatch, tmp_path):
    cfg = _prepare_cfg(tmp_path, "contenuto irrilevante")

    def fail_extract(path: Path):
        raise RuntimeError("boom")

    monkeypatch.setattr("api.ingestion.watcher._DOCUMENT_EXTRACTOR.extract", fail_extract)

    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]

    assert doc.status == "error"
    assert doc.error.startswith("extraction_failed")


@pytest.mark.asyncio
async def test_watcher_legacy_parity_when_flag_disabled(tmp_path):
    cfg = _prepare_cfg(tmp_path, "Lorem ipsum dolor sit amet. " * 40)
    settings = _make_settings(enable_classification=False)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    doc = docs[0]
    assert doc.chunking_strategy == "fallback::recursive_character_800_160"

    classification = doc.metadata["classification"]
    assert classification["status"] == "skipped"
    assert classification["reason"] == "feature_flag_disabled"

    # Story 6.3: DB-first storage - file system legacy behavior removed
    # Verify chunking strategy fallback logic works (no file verification needed)


@pytest.mark.asyncio
async def test_watcher_metrics_snapshot_accumulates(monkeypatch, tmp_path):
    sequence = [
        _stub_classification(DocumentStructureCategory.DOCUMENTO_TABELLARE, confidence=0.9),
        _stub_classification(DocumentStructureCategory.TESTO_ACCADEMICO_DENSO, confidence=0.95),
    ]

    def fake_classify(text: str, metadata):
        return sequence.pop(0)

    monkeypatch.setattr("api.ingestion.watcher.classify_content_enhanced", fake_classify)

    cfg = _prepare_cfg(tmp_path, "Prima riga\n\nSeconda riga")
    settings = _make_settings(enable_classification=True)

    docs = await scan_once(cfg, {}, settings=settings, conn=None)
    assert len(docs) == 1

    metrics = get_watcher_metrics_snapshot(settings)
    assert metrics["documents_processed"] >= 1
    assert metrics["classification"]["success"] == 1
    assert metrics["classification_latency_ms"]["count"] == 1
