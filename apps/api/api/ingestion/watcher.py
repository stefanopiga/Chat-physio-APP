from __future__ import annotations

import hashlib
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg

from api.config import Settings, get_settings
from api.diagnostics.redis_check import check_redis_health
from api.knowledge_base.classifier import classify_content_enhanced
from api.knowledge_base.classification_cache import (
    ClassificationCache,
    get_classification_cache,
)
from api.knowledge_base.extractors import DocumentExtractor

from .chunk_router import ChunkRouter, CONFIDENZA_SOGLIA_FALLBACK
from .config import IngestionConfig
from .db_storage import (
    get_document_by_hash,
    save_chunks_to_db,
    save_document_to_db,
    update_document_status,
)
from .models import ClassificazioneOutput, Document, EnhancedClassificationOutput
from .embedding_updater import update_embeddings_for_document  # Story 6.4 AC2 - UPDATE chunks esistenti
from .watcher_metrics import (
    get_metrics,
    get_watcher_metrics_snapshot,
    reset_watcher_metrics,
)

logger = logging.getLogger("api")

_DOCUMENT_EXTRACTOR = DocumentExtractor()
_CLASSIFICATION_EXECUTOR = ThreadPoolExecutor(max_workers=2)
METRICS = get_metrics()


class ClassificationTimeoutError(Exception):
    """Raised when the classification stage exceeds the configured timeout."""


def compute_file_hash(path: Path) -> str:
    """Compute deterministic SHA-256 hash for the provided file path."""
    sha = hashlib.sha256()
    with path.open("rb") as descriptor:
        for chunk in iter(lambda: descriptor.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _classify_with_timeout(
    text: str,
    extraction_metadata: Dict[str, Any],
    timeout_seconds: int,
    cache: ClassificationCache,
) -> tuple[EnhancedClassificationOutput, Dict[str, Any]]:
    """Execute classification respecting timeout and returning source metadata."""
    cache_stats_before = cache.get_stats() if cache else {}

    future = _CLASSIFICATION_EXECUTOR.submit(
        classify_content_enhanced,
        text,
        extraction_metadata,
    )
    try:
        classification = future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        future.cancel()
        raise ClassificationTimeoutError from exc

    cache_stats_after = cache.get_stats() if cache else {}
    source = "unknown"
    if cache_stats_before and cache_stats_after:
        hits_before = cache_stats_before.get("hits") or 0
        hits_after = cache_stats_after.get("hits") or 0
        misses_before = cache_stats_before.get("misses") or 0
        misses_after = cache_stats_after.get("misses") or 0
        if hits_after > hits_before:
            source = "cache"
        elif misses_after > misses_before:
            source = "llm"

    metadata = {
        "source": source,
        "cache": cache_stats_after,
    }
    return classification, metadata


async def _log_embedding_health_check(conn: asyncpg.Connection) -> None:
    """
    Log embedding coverage health check on watcher startup (Story 6.4 T3.2).
    
    Queries DB for embedding coverage and logs summary + warnings if coverage <100%.
    """
    try:
        # Query summary
        summary = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT d.id) AS total_documents,
                COUNT(dc.id) AS total_chunks,
                COUNT(dc.embedding) AS chunks_with_embeddings,
                COUNT(dc.id) - COUNT(dc.embedding) AS chunks_without_embeddings,
                ROUND(
                    (COUNT(dc.embedding)::numeric / NULLIF(COUNT(dc.id), 0)) * 100, 
                    2
                ) AS coverage_percent
            FROM documents d
            LEFT JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.status = 'completed'
        """)
        
        if not summary or summary['total_documents'] == 0:
            logger.info({
                "event": "watcher_embedding_health_check",
                "status": "no_documents",
                "message": "No completed documents found"
            })
            return
        
        coverage_percent = float(summary['coverage_percent'] or 0)
        chunks_without = summary['chunks_without_embeddings']
        
        log_data = {
            "event": "watcher_embedding_health_check",
            "total_documents": summary['total_documents'],
            "total_chunks": summary['total_chunks'],
            "chunks_with_embeddings": summary['chunks_with_embeddings'],
            "chunks_without_embeddings": chunks_without,
            "coverage_percent": coverage_percent
        }
        
        # WARNING if coverage <100%
        if coverage_percent < 100.0:
            # Query affected documents
            affected_docs = await conn.fetch("""
                SELECT d.id, d.file_name,
                       COUNT(dc.id) AS total_chunks,
                       COUNT(dc.embedding) AS with_embeddings
                FROM documents d
                LEFT JOIN document_chunks dc ON d.id = dc.document_id
                WHERE d.status = 'completed' 
                  AND d.id IN (
                      SELECT DISTINCT document_id 
                      FROM document_chunks 
                      WHERE embedding IS NULL
                  )
                GROUP BY d.id, d.file_name
            """)
            
            log_data["affected_documents"] = [
                {
                    "document_id": str(row['id']),
                    "file_name": row['file_name'],
                    "missing_embeddings": row['total_chunks'] - row['with_embeddings']
                }
                for row in affected_docs
            ]
            log_data["level"] = "WARNING"
            
            logger.warning(log_data)
        else:
            logger.info(log_data)
            
    except Exception as exc:
        logger.error({
            "event": "watcher_embedding_health_check_failed",
            "error": str(exc)
        })


async def scan_once(
    cfg: IngestionConfig,
    inventory: Dict[str, str],
    settings: Optional[Settings] = None,
    conn: Optional[asyncpg.Connection] = None,
) -> List[Document]:
    """
    Run a single watcher pass, extracting, classifying and chunking new/changed files.

    Implements AC2-AC4 by integrating the enhanced DocumentExtractor, routing decisions
    informed by LLM classification (guarded by feature flag + timeout), and structured
    logging/metrics required by AC7.
    
    Args:
        cfg: Ingestion configuration
        inventory: File hash inventory for change detection
        settings: Optional Settings instance (defaults to get_settings())
        conn: Optional asyncpg.Connection for DB storage (required for DB persistence)
    
    Returns:
        List of processed Document objects
    """
    resolved_settings = settings or get_settings()
    check_redis_health(resolved_settings)
    cache = get_classification_cache(resolved_settings)

    # Story 6.4 T3.2: Log embedding health check on startup
    if conn:
        await _log_embedding_health_check(conn)

    results: List[Document] = []
    for root, _, files in os.walk(cfg.watch_dir):
        for name in files:
            full = Path(root) / name
            if full.is_dir():
                continue

            try:
                file_hash = compute_file_hash(full)
            except Exception as exc:  # pragma: no cover - unreadable files
                logger.warning(
                    {
                        "event": "watcher_file_hash_error",
                        "file": str(full),
                        "error": str(exc),
                    }
                )
                continue

            # Story 6.3: Check in-memory inventory (fast path)
            previous_hash = inventory.get(str(full))
            if previous_hash == file_hash:
                continue
            
            # Story 6.3: Check DB for existing document (prevent re-ingestion)
            if conn:
                try:
                    existing_doc = await get_document_by_hash(conn, file_hash)
                    if existing_doc:
                        logger.info(
                            {
                                "event": "watcher_document_already_exists",
                                "file": str(full),
                                "file_hash": file_hash,
                                "document_id": str(existing_doc["id"]),
                                "existing_status": existing_doc["status"],
                                "created_at": str(existing_doc["created_at"]),
                            }
                        )
                        # Update inventory to skip on next pass
                        inventory[str(full)] = file_hash
                        continue  # Skip re-processing
                except Exception as db_check_exc:
                    # Log warning ma continua processing (fail-open per DB issues)
                    logger.warning(
                        {
                            "event": "watcher_db_check_error",
                            "file": str(full),
                            "error": str(db_check_exc),
                            "action": "continuing_processing",
                        }
                    )

            METRICS.record_document()
            doc = Document(
                file_name=name,
                file_path=str(full),
                file_hash=file_hash,
                status="pending",
                metadata={"size_bytes": full.stat().st_size},
            )

            extraction_duration_ms: Optional[float] = None
            try:
                extraction_started = time.perf_counter()
                extraction = _DOCUMENT_EXTRACTOR.extract(full)
                extraction_duration_ms = (time.perf_counter() - extraction_started) * 1000.0
            except Exception as exc:
                doc.status = "error"
                doc.error = f"extraction_failed: {exc}"
                logger.error(
                    {
                        "event": "watcher_extraction_error",
                        "file": str(full),
                        "file_extension": full.suffix.lower(),
                        "error": str(exc),
                    }
                )
                # DB storage for error case (if conn available)
                if conn:
                    try:
                        document_id = await save_document_to_db(
                            conn=conn,
                            file_name=name,
                            file_path=str(full),
                            file_hash=file_hash,
                            status="error",
                            metadata={"error": doc.error, **doc.metadata},
                        )
                        doc.metadata["document_id"] = str(document_id)
                    except Exception as db_exc:
                        logger.warning(
                            {
                                "event": "watcher_db_storage_error_doc_failed",
                                "file": str(full),
                                "error": str(db_exc),
                            }
                        )
                inventory[str(full)] = file_hash
                results.append(doc)
                continue

            try:
                text_content = extraction.get("text", "") or ""
                extraction_metadata = extraction.get("metadata", {}) or {}
                images_count = extraction_metadata.get(
                    "images_count", len(extraction.get("images", []))
                )
                tables_count = extraction_metadata.get(
                    "tables_count", len(extraction.get("tables", []))
                )

                doc.metadata.update(
                    {
                        "images_count": images_count,
                        "tables_count": tables_count,
                    }
                )

                logger.info(
                    {
                        "event": "watcher_extraction_complete",
                        "file": str(full),
                        "duration_ms": round(extraction_duration_ms or 0.0, 3),
                        "file_extension": full.suffix.lower(),
                        "text_length": len(text_content),
                        "metadata": {
                            "images_count": images_count,
                            "tables_count": tables_count,
                        },
                    }
                )

                classification_for_router: Optional[ClassificazioneOutput] = None
                classification_summary: Dict[str, Any] = {}
                classification_outcome = "skipped"
                classification_latency_ms: Optional[float] = None
                fallback_reason: Optional[str] = None

                if not text_content.strip():
                    fallback_reason = "empty_content"
                    classification_summary = {
                        "status": "skipped",
                        "reason": fallback_reason,
                    }
                    logger.info(
                        {
                            "event": "watcher_classification_skipped",
                            "file": str(full),
                            "reason": fallback_reason,
                        }
                    )
                elif not resolved_settings.watcher_enable_classification:
                    fallback_reason = "feature_flag_disabled"
                    classification_summary = {
                        "status": "skipped",
                        "reason": fallback_reason,
                    }
                    logger.info(
                        {
                            "event": "watcher_classification_skipped",
                            "file": str(full),
                            "reason": fallback_reason,
                        }
                    )
                else:
                    logger.info(
                        {
                            "event": "watcher_classification_start",
                            "file": str(full),
                            "timeout_seconds": resolved_settings.classification_timeout_seconds,
                            "metadata": {
                                "images_count": images_count,
                                "tables_count": tables_count,
                            },
                        }
                    )
                    started = time.perf_counter()
                    try:
                        classification_result, classification_meta = _classify_with_timeout(
                            text_content,
                            extraction_metadata,
                            resolved_settings.classification_timeout_seconds,
                            cache,
                        )
                        classification_latency_ms = (
                            time.perf_counter() - started
                        ) * 1000.0
                        classification_outcome = "success"
                        classification_summary = {
                            "status": "success",
                            "domain": classification_result.domain.value,
                            "structure_type": classification_result.structure_type.value,
                            "confidence": round(classification_result.confidence, 4),
                            "reasoning": classification_result.reasoning,
                            "detected_features": classification_result.detected_features,
                            "latency_ms": round(classification_latency_ms, 3),
                            "source": classification_meta.get("source"),
                            "cache_snapshot": classification_meta.get("cache"),
                        }
                        logger.info(
                            {
                                "event": "watcher_classification_success",
                                "file": str(full),
                                "latency_ms": round(classification_latency_ms, 3),
                                "confidence": classification_result.confidence,
                                "structure_type": classification_result.structure_type.value,
                                "domain": classification_result.domain.value,
                                "source": classification_summary["source"],
                            }
                        )
                        classification_for_router = ClassificazioneOutput(
                            classificazione=classification_result.structure_type,
                            motivazione=classification_result.reasoning,
                            confidenza=classification_result.confidence,
                        )
                    except ClassificationTimeoutError:
                        classification_outcome = "failure"
                        fallback_reason = "classification_timeout"
                        classification_summary = {
                            "status": "timeout",
                            "latency_ms": None,
                        }
                        logger.warning(
                            {
                                "event": "watcher_classification_timeout",
                                "file": str(full),
                                "timeout_seconds": resolved_settings.classification_timeout_seconds,
                            }
                        )
                    except Exception as exc:  # pragma: no cover - defensive
                        classification_outcome = "failure"
                        fallback_reason = "classification_error"
                        classification_summary = {
                            "status": "error",
                            "error": str(exc),
                        }
                        logger.warning(
                            {
                                "event": "watcher_classification_error",
                                "file": str(full),
                                "error": str(exc),
                            }
                        )

                METRICS.record_classification(
                    classification_outcome,
                    classification_latency_ms,
                )

                router = ChunkRouter()
                routing = router.route(
                    content=text_content,
                    classification=classification_for_router,
                )

                chunks = routing.chunks
                doc.chunking_strategy = routing.strategy_name
                doc.metadata.update(
                    {
                        "chunks_count": len(chunks),
                        "classification": classification_summary,
                        "routing": {
                            "strategy": routing.strategy_name,
                            "parameters": routing.parameters,
                        },
                    }
                )
                
                # DB Storage Integration (async with atomic transaction)
                if conn:
                    db_storage_start = time.perf_counter()
                    try:
                        async with conn.transaction():
                            # Step 1: Save document metadata
                            document_id = await save_document_to_db(
                                conn=conn,
                                file_name=name,
                                file_path=str(full),
                                file_hash=file_hash,
                                status="processing",
                                chunking_strategy=routing.strategy_name,
                                metadata=doc.metadata,
                            )
                            
                            # Step 2: Save chunks batch
                            # Include chunking strategy in chunk metadata for UI visibility
                            chunks_saved = await save_chunks_to_db(
                                conn=conn,
                                document_id=document_id,
                                chunks=chunks,
                                metadata={
                                    "file_name": name,
                                    "chunking_strategy": routing.strategy_name,
                                },
                            )
                            
                            # Step 3: Update document status to completed
                            await update_document_status(conn, document_id, "completed")
                        
                        db_storage_duration_ms = (time.perf_counter() - db_storage_start) * 1000.0
                        doc.status = "completed"
                        doc.metadata["document_id"] = str(document_id)
                        
                        # Story 6.4 AC2+AC2.5: UPDATE embeddings su chunk esistenti con advisory lock
                        # CRITICAL: Advisory lock BLOCKING per coordinamento con batch script
                        # DB-side hashtext() per key stability (NON Python hash())
                        if chunks:
                            try:
                                # Advisory lock BLOCKING - attende se batch attivo
                                # Pattern: dual-key namespace (hashtext('docs_ns'), hashtext(document_id))
                                await conn.execute("""
                                    SELECT pg_advisory_lock(hashtext('docs_ns'), hashtext($1::text))
                                """, str(document_id))
                                
                                logger.debug({
                                    "event": "indexing_lock_acquired",
                                    "document_id": str(document_id),
                                    "lock_type": "advisory_blocking"
                                })
                                
                                # UPDATE embeddings su chunk già salvati da save_chunks_to_db()
                                indexing_start = time.perf_counter()
                                updated = await update_embeddings_for_document(conn, document_id)
                                indexing_duration_ms = (time.perf_counter() - indexing_start) * 1000.0
                                
                                logger.info({
                                    "event": "watcher_indexing_complete",
                                    "file": str(full),
                                    "document_id": str(document_id),
                                    "chunks_updated": updated,
                                    "duration_ms": round(indexing_duration_ms, 3),
                                    "lock_coordinated": True
                                })
                                
                            except Exception as exc:
                                # Non bloccare ingestion - batch script è fallback
                                logger.warning({
                                    "event": "watcher_indexing_failed",
                                    "file": str(full),
                                    "document_id": str(document_id),
                                    "error": str(exc),
                                    "error_type": type(exc).__name__,
                                    "fallback": "batch_script_available"
                                })
                                
                            finally:
                                # Release lock sempre (anche in caso exception)
                                # CRITICAL: DB-side hashtext() deve corrispondere a chiave acquisita
                                await conn.execute("""
                                    SELECT pg_advisory_unlock(hashtext('docs_ns'), hashtext($1::text))
                                """, str(document_id))
                                
                                logger.debug({
                                    "event": "indexing_lock_released",
                                    "document_id": str(document_id)
                                })
                        
                        logger.info(
                            {
                                "event": "watcher_db_storage_complete",
                                "file": str(full),
                                "doc_id": str(document_id),
                                "duration_ms": round(db_storage_duration_ms, 3),
                                "status": "success",
                                "chunks_count": chunks_saved,
                            }
                        )
                    except Exception as db_exc:
                        db_storage_duration_ms = (time.perf_counter() - db_storage_start) * 1000.0
                        doc.status = "error"
                        doc.error = f"db_storage_failed: {db_exc}"
                        logger.error(
                            {
                                "event": "watcher_db_storage_failed",
                                "file": str(full),
                                "duration_ms": round(db_storage_duration_ms, 3),
                                "status": "failed",
                                "error": str(db_exc),
                            }
                        )
                else:
                    # No DB connection provided - backward compatibility (temporary)
                    doc.status = "chunked"
                    logger.warning(
                        {
                            "event": "watcher_db_storage_skipped",
                            "file": str(full),
                            "reason": "no_db_connection",
                        }
                    )

                is_fallback = routing.strategy_name.startswith("fallback::")
                low_confidence = (
                    classification_for_router is not None
                    and classification_for_router.confidenza < CONFIDENZA_SOGLIA_FALLBACK
                )
                if is_fallback and fallback_reason is None:
                    if classification_for_router is None:
                        fallback_reason = "classification_absent"
                    elif low_confidence:
                        fallback_reason = "low_confidence"
                    else:
                        fallback_reason = "unmapped_category"

                doc.metadata["routing"]["fallback"] = is_fallback
                doc.metadata["routing"]["fallback_reason"] = fallback_reason

                if is_fallback:
                    logger.info(
                        {
                            "event": "watcher_chunking_fallback",
                            "file": str(full),
                            "strategy": routing.strategy_name,
                            "fallback_reason": fallback_reason,
                            "confidence": classification_summary.get("confidence"),
                        }
                    )

                logger.info(
                    {
                        "event": "watcher_routing_decision",
                        "file": str(full),
                        "strategy": routing.strategy_name,
                        "chunks_count": len(chunks),
                        "fallback": is_fallback,
                        "fallback_reason": fallback_reason,
                        "classification_confidence": classification_summary.get("confidence"),
                    }
                )

                METRICS.record_strategy(routing.strategy_name, is_fallback)

            except Exception as exc:
                doc.status = "error"
                doc.error = str(exc)
                logger.error(
                    {
                        "event": "watcher_processing_error",
                        "file": str(full),
                        "error": str(exc),
                    }
                )
                # DB storage for processing error (if conn available)
                if conn:
                    try:
                        document_id = await save_document_to_db(
                            conn=conn,
                            file_name=name,
                            file_path=str(full),
                            file_hash=file_hash,
                            status="error",
                            metadata={"error": doc.error, **doc.metadata},
                        )
                        doc.metadata["document_id"] = str(document_id)
                    except Exception as db_exc:
                        logger.warning(
                            {
                                "event": "watcher_db_storage_processing_error_failed",
                                "file": str(full),
                                "error": str(db_exc),
                            }
                        )

            inventory[str(full)] = file_hash
            results.append(doc)

    if results:
        metrics_snapshot = get_watcher_metrics_snapshot(resolved_settings)
        logger.info(
            {
                "event": "watcher_metrics_snapshot",
                "metrics": metrics_snapshot,
            }
        )

    return results


__all__ = [
    "ClassificationTimeoutError",
    "compute_file_hash",
    "get_watcher_metrics_snapshot",
    "reset_watcher_metrics",
    "scan_once",
]
