import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from api.ingestion.config import IngestionConfig
from api.ingestion.watcher import reset_watcher_metrics, scan_once


def _make_settings(enable_classification: bool = False):
    return SimpleNamespace(
        watcher_enable_classification=enable_classification,
        classification_timeout_seconds=10,
        classification_cache_enabled=False,
        classification_cache_ttl_seconds=600,
        classification_cache_redis_url=None,
        celery_broker_url="redis://localhost:6379/0",
    )



@pytest.mark.asyncio
async def test_scan_crea_output_temporanei(tmp_path: Path, monkeypatch):
    reset_watcher_metrics()
    watch = tmp_path / "watch"
    temp = tmp_path / "temp"
    os.makedirs(watch, exist_ok=True)
    os.makedirs(temp, exist_ok=True)

    cfg = IngestionConfig(watch_dir=watch, temp_dir=temp)

    f = watch / "a.txt"
    f.write_text("hello", encoding="utf-8")

    inventory = {}
    docs = await scan_once(cfg, inventory, settings=_make_settings(), conn=None)

    assert len(docs) == 1
    d = docs[0]
    assert d.status in {"chunked", "error"}
    
    # Story 6.3: DB-first storage - legacy file output removed
    # Verify document processing and hash generation (no file verification)
    assert d.file_hash is not None
    assert d.metadata.get("chunks_count", 0) > 0

    # modifica il file -> nuovo hash, nuova registrazione
    f.write_text("hello world", encoding="utf-8")
    docs2 = await scan_once(cfg, inventory, settings=_make_settings(), conn=None)
    assert len(docs2) == 1
    assert docs2[0].file_hash != d.file_hash


@pytest.mark.asyncio
async def test_ingestion_metadata_chunking(tmp_path: Path):
    reset_watcher_metrics()
    watch = tmp_path / "watch"
    temp = tmp_path / "temp"
    os.makedirs(watch, exist_ok=True)
    os.makedirs(temp, exist_ok=True)

    cfg = IngestionConfig(watch_dir=watch, temp_dir=temp)
    f = watch / "a.txt"
    f.write_text("hello world" * 100, encoding="utf-8")

    docs = await scan_once(cfg, {}, settings=_make_settings(), conn=None)
    assert len(docs) == 1
    d = docs[0]
    assert d.status == "chunked"
    assert d.chunking_strategy and isinstance(d.chunking_strategy, str)
    assert d.metadata.get("chunks_count", 0) > 0
    
    # Story 6.3: DB-first storage - chunks saved to DB, not filesystem
    # Verify metadata without checking temp directory structure
