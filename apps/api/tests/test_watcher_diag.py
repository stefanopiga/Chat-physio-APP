import json
import sys
from pathlib import Path

import pytest

from api.ingestion.chunking.strategy import ChunkingResult
from api.ingestion.models import (
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)


def _set_min_env(monkeypatch, tmp_path: Path) -> Path:
    env_vars = {
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "service-key",
        "SUPABASE_JWT_SECRET": "jwt-secret",
        "OPENAI_API_KEY": "sk-test",
        "DATABASE_URL": "postgresql://localhost/test",
        "INGESTION_WATCH_DIR": str(tmp_path / "watch"),
        "INGESTION_TEMP_DIR": str(tmp_path / "temp"),
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return Path(env_vars["INGESTION_TEMP_DIR"])


def test_run_diag_generates_report(monkeypatch, tmp_path, capsys):
    temp_dir = _set_min_env(monkeypatch, tmp_path)

    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("Example document content for diagnostics.", encoding="utf-8")

    from api.ingestion import run_diag

    monkeypatch.setattr(run_diag, "load_dotenv", lambda override=True: None)

    fake_classification = EnhancedClassificationOutput(
        domain=ContentDomain.ANATOMIA,
        structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
        confidence=0.92,
        reasoning="deterministic reasoning",
        detected_features={"has_images": False, "has_tables": False},
    )

    monkeypatch.setattr(
        run_diag,
        "_classify_with_timeout",
        lambda text, meta, timeout, cache: (fake_classification, {"source": "test"}),
    )
    monkeypatch.setattr(
        run_diag,
        "get_classification_cache",
        lambda settings: object(),
    )
    monkeypatch.setattr(
        run_diag,
        "check_redis_health",
        lambda settings: {
            "enabled": True,
            "healthy": True,
            "latency_ms": 1.2,
            "redis_url": "redis://test",
        },
    )

    class DummyRouter:
        def route(self, content, classification):
            return ChunkingResult(
                chunks=["chunk-one", "chunk-two"],
                strategy_name="dummy_strategy",
                parameters={"chunk_size": 1000},
            )

    monkeypatch.setattr(run_diag, "ChunkRouter", DummyRouter)

    monkeypatch.setattr(
        sys,
        "argv",
        ["run_diag.py", "--file", str(sample_file)],
    )

    with pytest.raises(SystemExit) as exc:
        run_diag.main()

    assert exc.value.code == 0

    captured = capsys.readouterr().out
    assert "Chunking used strategy 'dummy_strategy'" in captured

    diag_dir = temp_dir / "diag"
    reports = list(diag_dir.glob("*.json"))
    assert reports, "Expected diagnostic report to be generated"

    report_data = json.loads(reports[0].read_text(encoding="utf-8"))
    assert report_data["classification"]["status"] == "success"
    assert report_data["routing"]["strategy"] == "dummy_strategy"
    assert report_data["redis_health"]["healthy"] is True
