"""
Embedding updater per chunk già esistenti nel DB (Story 6.4).

Questo modulo fornisce funzioni per aggiornare embeddings su chunk già salvati,
invece di creare nuovi chunk (diverso da index_chunks che usa add_texts).
"""
import logging
import time
from typing import List, Dict, Any
import uuid
import asyncpg

from langchain_openai import OpenAIEmbeddings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import openai

logger = logging.getLogger("api")


@retry(
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
async def update_embeddings_for_document(
    conn: asyncpg.Connection,
    document_id: uuid.UUID,
) -> int:
    """
    Aggiorna embeddings per tutti i chunk di un documento già salvati.
    
    Pattern Story 6.4:
    - Query chunk esistenti con embedding IS NULL
    - Genera embeddings batch con OpenAI
    - UPDATE sui chunk esistenti (non INSERT nuovi)
    
    Args:
        conn: asyncpg connection
        document_id: UUID documento da processare
        
    Returns:
        Numero di chunk aggiornati
    """
    start_time = time.time()
    
    # Query chunk senza embeddings
    rows = await conn.fetch("""
        SELECT id, content 
        FROM document_chunks 
        WHERE document_id = $1 
          AND embedding IS NULL
        ORDER BY id
    """, document_id)
    
    if not rows:
        logger.debug({
            "event": "no_chunks_to_update",
            "document_id": str(document_id)
        })
        return 0
    
    chunk_ids = [row['id'] for row in rows]
    contents = [row['content'] for row in rows]
    
    logger.info({
        "event": "embedding_update_start",
        "document_id": str(document_id),
        "chunks_count": len(contents)
    })
    
    # Genera embeddings con retry automatico
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    
    BATCH_SIZE = 100
    all_embeddings = []
    
    for i in range(0, len(contents), BATCH_SIZE):
        batch = contents[i:i + BATCH_SIZE]
        batch_embeddings = embeddings_model.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        
        logger.debug({
            "event": "embedding_batch_generated",
            "batch_num": i // BATCH_SIZE + 1,
            "batch_size": len(batch)
        })
    
    # UPDATE batch sui chunk esistenti
    update_start = time.time()
    
    # Serializza embeddings come stringhe per PostgreSQL vector type
    # Formato: '[0.1, 0.2, 0.3, ...]'
    records = [
        (chunk_ids[i], str(all_embeddings[i])) 
        for i in range(len(chunk_ids))
    ]
    
    # Batch UPDATE con executemany
    await conn.executemany("""
        UPDATE document_chunks 
        SET 
            embedding = $2::vector(1536),
            updated_at = NOW()
        WHERE id = $1
    """, records)
    
    update_duration_ms = int((time.time() - update_start) * 1000)
    total_duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info({
        "event": "embedding_update_complete",
        "document_id": str(document_id),
        "chunks_updated": len(chunk_ids),
        "update_ms": update_duration_ms,
        "total_ms": total_duration_ms
    })
    
    return len(chunk_ids)

