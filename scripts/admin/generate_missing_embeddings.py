#!/usr/bin/env python3
"""
Script batch per generare embeddings mancanti (Story 6.4 AC1 + AC2.5).

CRITICAL - Advisory Lock Pattern (Architetto 2025-10-20):
- Non-blocking lock: pg_try_advisory_lock() → skip documento se locked da watcher
- DB-side hashtext() per key stability (NON Python hash())
- Coordinamento garantito con watcher (entrambi usano advisory locks)

Usage:
    poetry --directory apps/api run python scripts/admin/generate_missing_embeddings.py

Architecture References:
- docs/architecture/addendum-asyncpg-database-pattern.md - Pattern 6
- docs/qa/assessments/6.4.*-test-design-*.md - AC2.5 test requirements
"""
import asyncio
import asyncpg
import logging
import sys
import time
from typing import List, Dict, Any
from pathlib import Path

# Add apps/api to path per import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "api"))

from api.ingestion.embedding_updater import update_embeddings_for_document
from api.config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def process_documents_with_advisory_locks():
    """
    Processa documenti con chunk mancanti usando advisory locks per coordinamento.
    
    Pattern AC2.5 (Architetto):
    - Query documenti standard (NO FOR UPDATE SKIP LOCKED)
    - Per ogni documento: tentare pg_try_advisory_lock() non-bloccante
    - Se locked da watcher: skip con log batch_doc_skipped
    - Se acquisito: processa + release in finally
    - DB-side hashtext() per key stability cross-process
    """
    import os
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL non impostata in .env")
    
    conn: asyncpg.Connection = await asyncpg.connect(database_url, statement_cache_size=0)
    
    try:
        # Query documenti completati (NO row-level locks - coordinamento via advisory)
        docs = await conn.fetch("""
            SELECT d.id, d.file_name
            FROM documents d
            WHERE d.status = 'completed'
            ORDER BY d.updated_at DESC
        """)
        
        logger.info({
            "event": "batch_start",
            "documents_found": len(docs),
            "strategy": "advisory_locks_nonblocking"
        })
        
        total_indexed = 0
        total_skipped = 0
        total_docs_processed = 0
        start_time = time.time()
        
        for doc in docs:
            doc_id = str(doc['id'])
            doc_name = doc['file_name']
            
            # CRITICAL: Non-blocking advisory lock con DB-side hashtext()
            # Pattern: dual-key namespace (hashtext('docs_ns'), hashtext(document_id))
            locked = await conn.fetchval("""
                SELECT pg_try_advisory_lock(
                    hashtext('docs_ns'), 
                    hashtext($1::text)
                )
            """, doc_id)
            
            if not locked:
                # Watcher sta processando documento - skip senza errore
                logger.info({
                    "event": "batch_doc_skipped",
                    "reason": "locked_by_watcher",
                    "document_id": doc_id,
                    "document_name": doc_name
                })
                total_skipped += 1
                continue
            
            try:
                # UPDATE embeddings su chunk esistenti (evita duplicati)
                doc_start = time.time()
                updated = await update_embeddings_for_document(conn, doc['id'])
                doc_duration_ms = int((time.time() - doc_start) * 1000)
                
                if updated == 0:
                    logger.debug({
                        "event": "batch_doc_already_indexed",
                        "document_id": doc_id,
                        "document_name": doc_name
                    })
                    continue
                
                logger.info({
                    "event": "batch_doc_indexed",
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "chunks_updated": updated,
                    "duration_ms": doc_duration_ms
                })
                
                total_indexed += updated
                total_docs_processed += 1
                
            except Exception as exc:
                logger.error({
                    "event": "batch_doc_failed",
                    "document_id": doc_id,
                    "document_name": doc_name,
                    "error": str(exc),
                    "error_type": type(exc).__name__
                })
                # Continue con altri documenti
                
            finally:
                # CRITICAL: Release lock sempre (anche in caso exception)
                # DB-side hashtext() deve corrispondere a chiave acquisita
                await conn.execute("""
                    SELECT pg_advisory_unlock(
                        hashtext('docs_ns'), 
                        hashtext($1::text)
                    )
                """, doc_id)
                
                logger.debug({
                    "event": "batch_lock_released",
                    "document_id": doc_id
                })
        
        # Metriche finali
        total_duration_s = time.time() - start_time
        
        logger.info({
            "event": "batch_complete",
            "documents_processed": total_docs_processed,
            "documents_skipped": total_skipped,
            "chunks_indexed": total_indexed,
            "duration_s": round(total_duration_s, 2),
            "chunks_per_second": round(total_indexed / total_duration_s, 2) if total_duration_s > 0 else 0
        })
        
        # Output user-friendly per shell
        print(f"\n✅ Batch indexing completato:")
        print(f"  • Documenti processati: {total_docs_processed}")
        print(f"  • Documenti skipped (locked): {total_skipped}")
        print(f"  • Chunk indicizzati: {total_indexed}")
        print(f"  • Durata: {round(total_duration_s, 2)}s")
        print(f"  • Throughput: {round(total_indexed / total_duration_s, 2)} chunk/s\n")
        
        # Exit code per automation
        return 0 if total_indexed > 0 or total_docs_processed == 0 else 1
        
    finally:
        await conn.close()


async def verify_embedding_coverage():
    """Verifica coverage embeddings post-batch per validazione."""
    import os
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL non impostata in .env")
    
    conn: asyncpg.Connection = await asyncpg.connect(database_url, statement_cache_size=0)
    
    try:
        result = await conn.fetchrow("""
            SELECT 
                COUNT(*) AS total_chunks,
                COUNT(embedding) AS with_embeddings,
                COUNT(*) - COUNT(embedding) AS without_embeddings,
                ROUND(
                    (COUNT(embedding)::numeric / NULLIF(COUNT(*), 0)) * 100, 
                    2
                ) AS coverage_percent
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'completed'
        """)
        
        logger.info({
            "event": "embedding_coverage_verification",
            "total_chunks": result['total_chunks'],
            "with_embeddings": result['with_embeddings'],
            "without_embeddings": result['without_embeddings'],
            "coverage_percent": float(result['coverage_percent'] or 0)
        })
        
        print(f"\n📊 Coverage embeddings:")
        print(f"  • Chunk totali: {result['total_chunks']}")
        print(f"  • Con embeddings: {result['with_embeddings']}")
        print(f"  • Senza embeddings: {result['without_embeddings']}")
        print(f"  • Coverage: {result['coverage_percent']}%\n")
        
    finally:
        await conn.close()


async def main():
    """Entry point con error handling."""
    try:
        logger.info({
            "event": "batch_script_start",
            "pattern": "advisory_locks",
            "lock_type": "non_blocking"
        })
        
        exit_code = await process_documents_with_advisory_locks()
        
        # Verifica coverage post-batch
        await verify_embedding_coverage()
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.warning("Script interrotto da utente")
        sys.exit(130)
        
    except Exception as exc:
        logger.error({
            "event": "batch_script_fatal_error",
            "error": str(exc),
            "error_type": type(exc).__name__
        })
        print(f"\n❌ Errore fatale: {exc}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
