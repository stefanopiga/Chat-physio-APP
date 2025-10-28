"""
Document persistence layer for database operations.

Provides functions for:
- Inserting/updating documents with idempotency (ON CONFLICT)
- Updating document status post-indexing
- Managing document lifecycle
- Checking for existing documents (duplicate detection)

Pattern: asyncpg with parametrized queries
Reference: docs/architecture/addendum-asyncpg-database-pattern.md
"""

import json
import uuid
from typing import Optional, Dict, Any
import asyncpg


async def get_document_by_hash(
    conn: asyncpg.Connection,
    file_hash: str,
) -> Optional[Dict[str, Any]]:
    """
    Recupera documento esistente tramite file_hash per prevenire re-ingestion.
    
    Args:
        conn: asyncpg connection dal pool
        file_hash: SHA-256 hash del file da controllare
    
    Returns:
        Dict con {id, file_name, file_path, status, created_at, updated_at} se esiste,
        None se documento non trovato
    
    Usage (Story 6.3 - duplicate prevention):
        >>> existing = await get_document_by_hash(conn, "abc123...")
        >>> if existing:
        ...     logger.info(f"Document already processed: {existing['id']}")
        ...     continue  # Skip re-processing
    """
    query = """
        SELECT id, file_name, file_path, file_hash, status, 
               created_at, updated_at
        FROM documents
        WHERE file_hash = $1
        LIMIT 1
    """
    row = await conn.fetchrow(query, file_hash)
    
    if not row:
        return None
    
    return {
        "id": row["id"],
        "file_name": row["file_name"],
        "file_path": row["file_path"],
        "file_hash": row["file_hash"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def save_document_to_db(
    conn: asyncpg.Connection,
    file_name: str,
    file_path: str,
    file_hash: str,
    status: str = "processing",
    chunking_strategy: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> uuid.UUID:
    """
    Inserisce o aggiorna documento in tabella documents.
    
    Args:
        conn: asyncpg connection dal pool
        file_name: Nome file sorgente
        file_path: Path file sorgente
        file_hash: SHA-256 hash del contenuto (per deduplicazione)
        status: Status documento (processing, completed, error)
        chunking_strategy: Strategia chunking applicata (opzionale)
        metadata: Metadata aggiuntivi in formato JSONB (opzionale)
    
    Returns:
        UUID del documento (nuovo o esistente)
    
    Idempotency:
        ON CONFLICT (file_hash) DO UPDATE garantisce update su re-ingestion.
        Il document_id rimane invariato per stesso file_hash.
    
    Example:
        >>> doc_id = await save_document_to_db(
        ...     conn=conn,
        ...     file_name="test.pdf",
        ...     file_path="/path/test.pdf",
        ...     file_hash="abc123...",
        ...     status="processing",
        ...     chunking_strategy="recursive_800",
        ...     metadata={"size_bytes": 12345}
        ... )
    """
    query = """
        INSERT INTO documents (
            id, file_name, file_path, file_hash,
            status, chunking_strategy, metadata,
            created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
        ON CONFLICT (file_hash) DO UPDATE SET
            status = EXCLUDED.status,
            chunking_strategy = EXCLUDED.chunking_strategy,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        RETURNING id
    """
    
    document_id = uuid.uuid4()
    
    # Serialize metadata dict to JSON string for JSONB parameter
    metadata_json = json.dumps(metadata) if metadata else json.dumps({})
    
    # Serialize chunking_strategy to JSON string for JSONB parameter
    # If string is passed, convert to {"type": "string_value"}
    if chunking_strategy:
        if isinstance(chunking_strategy, str):
            chunking_strategy_json = json.dumps({"type": chunking_strategy})
        else:
            chunking_strategy_json = json.dumps(chunking_strategy)
    else:
        chunking_strategy_json = None
    
    result_id = await conn.fetchval(
        query,
        document_id,
        file_name,
        file_path,
        file_hash,
        status,
        chunking_strategy_json,
        metadata_json,
    )
    
    return result_id


async def update_document_status(
    conn: asyncpg.Connection,
    document_id: uuid.UUID,
    status: str,
    error: Optional[str] = None,
) -> None:
    """
    Aggiorna status documento post-indexing.
    
    Args:
        conn: asyncpg connection dal pool
        document_id: UUID documento da aggiornare
        status: Nuovo status (completed, error)
        error: Messaggio errore (opzionale, solo if status=error)
    
    Status Values:
        - processing: Indexing in corso
        - completed: Indexing completato con successo
        - error: Indexing fallito
    
    Example:
        >>> await update_document_status(
        ...     conn=conn,
        ...     document_id=uuid.UUID("..."),
        ...     status="completed"
        ... )
        
        >>> await update_document_status(
        ...     conn=conn,
        ...     document_id=uuid.UUID("..."),
        ...     status="error",
        ...     error="Embedding API timeout"
        ... )
    """
    if error:
        query = """
            UPDATE documents
            SET 
                status = $1,
                metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{error}',
                    to_jsonb($2::text)
                ),
                updated_at = NOW()
            WHERE id = $3
        """
        await conn.execute(query, status, error, document_id)
    else:
        query = """
            UPDATE documents
            SET status = $1, updated_at = NOW()
            WHERE id = $2
        """
        await conn.execute(query, status, document_id)


async def save_chunks_to_db(
    conn: asyncpg.Connection,
    document_id: uuid.UUID,
    chunks: list[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Salva chunks nel database senza calcolare embeddings.
    Gli embeddings possono essere aggiunti successivamente.
    
    Args:
        conn: asyncpg connection dal pool
        document_id: UUID documento parent
        chunks: Lista di chunk testuali da salvare
        metadata: Metadata opzionali da associare ai chunks
    
    Returns:
        Numero di chunks inseriti
    
    Note:
        - Gli embeddings sono NULL al momento dell'inserimento
        - I chunks vengono salvati in ordine sequenziale
        - chunk_index viene assegnato automaticamente (0-based)
    
    Example:
        >>> count = await save_chunks_to_db(
        ...     conn=conn,
        ...     document_id=doc_id,
        ...     chunks=["chunk 1 text", "chunk 2 text"],
        ...     metadata={"source": "watcher"}
        ... )
    """
    if not chunks:
        return 0
    
    # Prepara batch di record da inserire
    records = []
    base_metadata = metadata or {}
    
    for idx, chunk_text in enumerate(chunks):
        chunk_metadata = {
            **base_metadata,
            "chunk_index": idx,
            "chunk_size": len(chunk_text),
        }
        
        records.append((
            uuid.uuid4(),  # id
            document_id,   # document_id
            chunk_text,    # content
            None,          # embedding (NULL per ora)
            json.dumps(chunk_metadata),  # metadata
        ))
    
    # Batch insert
    query = """
        INSERT INTO document_chunks (id, document_id, content, embedding, metadata, created_at, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
    """
    
    await conn.executemany(query, records)
    
    return len(records)

