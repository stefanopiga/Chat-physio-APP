from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from api.config import get_settings
from api.diagnostics.redis_check import check_redis_health
from api.ingestion.chunk_router import ChunkRouter, CONFIDENZA_SOGLIA_FALLBACK
from api.ingestion.config import IngestionConfig
from api.ingestion.models import ClassificazioneOutput
from api.ingestion.watcher import (
    ClassificationTimeoutError,
    _classify_with_timeout,
    compute_file_hash,
    get_watcher_metrics_snapshot,
)
from api.knowledge_base.classification_cache import get_classification_cache
from api.knowledge_base.extractors import DocumentExtractor

logger = logging.getLogger("api")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run watcher ingestion pipeline diagnostics on a single file.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the document to process",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(override=True)
    args = parse_args()
    target = Path(args.file).expanduser().resolve()
    if not target.exists() or not target.is_file():
        print(f"[!] File not found: {target}", file=sys.stderr)
        sys.exit(1)

    settings = get_settings()
    cfg = IngestionConfig.from_env(settings)
    diag_dir = cfg.temp_dir / "diag"
    diag_dir.mkdir(parents=True, exist_ok=True)

    redis_health = check_redis_health(settings)
    cache = get_classification_cache(settings)

    extractor = DocumentExtractor()
    timings: Dict[str, float] = {}
    classification_summary: Dict[str, Any] = {}
    classification_for_router: Optional[ClassificazioneOutput] = None
    fallback_reason: Optional[str] = None
    exit_code = 0

    logger.info(
        {
            "event": "run_diag_start",
            "file": str(target),
            "watch_dir": str(cfg.watch_dir),
            "temp_dir": str(cfg.temp_dir),
        }
    )

    extraction_started = time.perf_counter()
    extraction = extractor.extract(target)
    timings["extraction_ms"] = round(
        (time.perf_counter() - extraction_started) * 1000.0, 3
    )

    text_content = extraction.get("text", "") or ""
    extraction_metadata = extraction.get("metadata", {}) or {}
    images_count = extraction_metadata.get(
        "images_count", len(extraction.get("images", []))
    )
    tables_count = extraction_metadata.get(
        "tables_count", len(extraction.get("tables", []))
    )

    print(f"[+] Extraction completed in {timings['extraction_ms']} ms")
    print(f"    Text length: {len(text_content)} characters")
    print(f"    Images: {images_count} | Tables: {tables_count}")

    if not text_content.strip():
        fallback_reason = "empty_content"
        classification_summary = {
            "status": "skipped",
            "reason": fallback_reason,
        }
    elif not settings.watcher_enable_classification:
        fallback_reason = "feature_flag_disabled"
        classification_summary = {
            "status": "skipped",
            "reason": fallback_reason,
        }
    else:
        classification_started = time.perf_counter()
        try:
            classification_result, classification_meta = _classify_with_timeout(
                text_content,
                extraction_metadata,
                settings.classification_timeout_seconds,
                cache,
            )
            timings["classification_ms"] = round(
                (time.perf_counter() - classification_started) * 1000.0, 3
            )
            classification_summary = {
                "status": "success",
                "domain": classification_result.domain.value,
                "structure_type": classification_result.structure_type.value,
                "confidence": round(classification_result.confidence, 4),
                "reasoning": classification_result.reasoning,
                "detected_features": classification_result.detected_features,
                "latency_ms": timings["classification_ms"],
                "source": classification_meta.get("source"),
            }
            classification_for_router = ClassificazioneOutput(
                classificazione=classification_result.structure_type,
                motivazione=classification_result.reasoning,
                confidenza=classification_result.confidence,
            )
            print(
                f"[+] Classification completed in {timings['classification_ms']} ms "
                f"(domain={classification_summary['domain']}, "
                f"struct={classification_summary['structure_type']}, "
                f"confidence={classification_summary['confidence']})"
            )
        except ClassificationTimeoutError:
            timings["classification_ms"] = round(
                (time.perf_counter() - classification_started) * 1000.0, 3
            )
            classification_summary = {
                "status": "timeout",
                "latency_ms": timings["classification_ms"],
                "timeout_seconds": settings.classification_timeout_seconds,
            }
            fallback_reason = "classification_timeout"
            exit_code = max(exit_code, 2)
            print(
                f"[!] Classification timed out after "
                f"{settings.classification_timeout_seconds}s"
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            timings["classification_ms"] = round(
                (time.perf_counter() - classification_started) * 1000.0, 3
            )
            classification_summary = {
                "status": "error",
                "error": str(exc),
                "latency_ms": timings["classification_ms"],
            }
            fallback_reason = "classification_error"
            exit_code = max(exit_code, 3)
            print(f"[!] Classification error: {exc}")

    router = ChunkRouter()
    chunk_started = time.perf_counter()
    routing = router.route(text_content, classification_for_router)
    timings["chunking_ms"] = round(
        (time.perf_counter() - chunk_started) * 1000.0, 3
    )
    chunks = routing.chunks
    is_fallback = routing.strategy_name.startswith("fallback::")
    if is_fallback and fallback_reason is None:
        if classification_for_router is None:
            fallback_reason = "classification_absent"
        elif classification_for_router.confidenza < CONFIDENZA_SOGLIA_FALLBACK:
            fallback_reason = "low_confidence"
        else:
            fallback_reason = "unmapped_category"

    print(
        f"[+] Chunking used strategy '{routing.strategy_name}' "
        f"in {timings['chunking_ms']} ms producing {len(chunks)} chunks"
    )
    if is_fallback:
        print(f"    Fallback reason: {fallback_reason}")

    report = {
        "file": str(target),
        "file_hash": compute_file_hash(target),
        "timings_ms": timings,
        "classification": classification_summary,
        "routing": {
            "strategy": routing.strategy_name,
            "fallback": is_fallback,
            "fallback_reason": fallback_reason,
            "parameters": routing.parameters,
            "chunks_count": len(chunks),
            "chunk_lengths": [len(chunk) for chunk in chunks[:3]],
        },
        "redis_health": redis_health,
        "metrics_snapshot": get_watcher_metrics_snapshot(settings),
    }

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_path = diag_dir / f"{timestamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"[+] Diagnostic report saved to {report_path}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

