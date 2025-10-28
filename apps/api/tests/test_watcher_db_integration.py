"""
Test per integrazione DB watcher - Story 6.1/6.2/6.3 DB storage.

Copertura:
- save_chunks_to_db: salvataggio chunks senza embeddings
- save_document_to_db: salvataggio documento con metadata
- DB-first integration (Story 6.3)
"""

import pytest
import uuid
from unittest.mock import AsyncMock

from api.ingestion.db_storage import save_document_to_db, save_chunks_to_db


@pytest.fixture
def mock_db_conn():
    """Mock asyncpg.Connection per unit test isolati."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    conn.executemany = AsyncMock()
    conn.fetch = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_save_chunks_to_db_basic(mock_db_conn):
    """
    Given: Un documento con ID valido
    When: save_chunks_to_db viene chiamato con una lista di chunks
    Then: executemany viene chiamato con i parametri corretti
    """
    doc_id = uuid.uuid4()
    
    # Action: salva chunks
    chunks = ["Chunk 1 content", "Chunk 2 content", "Chunk 3 content"]
    saved_count = await save_chunks_to_db(
        conn=mock_db_conn,
        document_id=doc_id,
        chunks=chunks,
        metadata={"source": "test"}
    )
    
    # Assert: count corretto
    assert saved_count == 3
    
    # Assert: executemany chiamato una volta
    assert mock_db_conn.executemany.call_count == 1
    
    # Assert: query corretta
    call_args = mock_db_conn.executemany.call_args
    query = call_args[0][0]
    records = call_args[0][1]
    
    assert "INSERT INTO document_chunks" in query
    assert "embedding" in query
    assert len(records) == 3
    
    # Verifica struttura records
    assert records[0][1] == doc_id  # document_id
    assert records[0][2] == "Chunk 1 content"  # content
    assert records[0][3] is None  # embedding NULL


@pytest.mark.asyncio
async def test_save_chunks_to_db_empty_list(mock_db_conn):
    """
    Given: Lista chunks vuota
    When: save_chunks_to_db viene chiamato
    Then: Ritorna 0 senza chiamare executemany
    """
    doc_id = uuid.uuid4()
    
    saved_count = await save_chunks_to_db(
        conn=mock_db_conn,
        document_id=doc_id,
        chunks=[],  # Lista vuota
    )
    
    assert saved_count == 0
    assert mock_db_conn.executemany.call_count == 0


@pytest.mark.asyncio
async def test_save_chunks_to_db_metadata_optional(mock_db_conn):
    """
    Given: Chunks senza metadata extra
    When: save_chunks_to_db viene chiamato con metadata=None
    Then: I chunks vengono salvati con metadata minimale (chunk_index, chunk_size)
    """
    doc_id = uuid.uuid4()
    
    chunks = ["Short", "Medium length chunk", "Very long chunk"]
    saved_count = await save_chunks_to_db(
        conn=mock_db_conn,
        document_id=doc_id,
        chunks=chunks,
        metadata=None  # Nessun metadata extra
    )
    
    assert saved_count == 3
    
    # Verifica che executemany sia stato chiamato
    call_args = mock_db_conn.executemany.call_args
    records = call_args[0][1]
    
    # Verifica metadata nel primo record (JSON string)
    import json
    metadata_0 = json.loads(records[0][4])
    assert metadata_0["chunk_index"] == 0
    assert metadata_0["chunk_size"] == len("Short")
    
    metadata_1 = json.loads(records[1][4])
    assert metadata_1["chunk_index"] == 1
    assert metadata_1["chunk_size"] == len("Medium length chunk")


@pytest.mark.asyncio
async def test_save_document_to_db_with_metadata(mock_db_conn):
    """
    Given: Documento con metadata complessi
    When: save_document_to_db viene chiamato
    Then: Il documento viene salvato con metadata serializzati correttamente
    """
    doc_id = uuid.uuid4()
    mock_db_conn.fetchval.return_value = doc_id
    
    metadata = {
        "chunks_count": 10,
        "classification": {"domain": "medical", "confidence": 0.95},
        "routing": {"strategy": "recursive_800", "parameters": {"overlap": 160}},
    }
    
    returned_id = await save_document_to_db(
        conn=mock_db_conn,
        file_name="test.pdf",
        file_path="/tmp/test.pdf",
        file_hash="abc123",
        status="processing",
        chunking_strategy="recursive_800_160",
        metadata=metadata,
    )
    
    assert returned_id == doc_id
    assert mock_db_conn.fetchval.call_count == 1
    
    # Verifica query chiamata
    call_args = mock_db_conn.fetchval.call_args
    query = call_args[0][0]
    assert "INSERT INTO documents" in query
    assert "ON CONFLICT (file_hash)" in query  # Idempotenza


@pytest.mark.asyncio
async def test_db_first_pipeline_direct(mock_db_conn):
    """
    Test integrazione DB-first: watcher -> DB direttamente (Story 6.3)
    
    Workflow nuovo:
    1. Watcher crea documento nel DB
    2. Watcher salva chunks direttamente nel DB
    3. Nessun storage filesystem intermedio
    """
    file_hash = "db_first_hash"
    doc_id = uuid.uuid4()
    
    # Setup mock
    mock_db_conn.fetchval.return_value = doc_id
    
    # Step 1: Salva documento nel DB
    returned_id = await save_document_to_db(
        conn=mock_db_conn,
        file_name="direct_pipeline.pdf",
        file_path="/watch/direct_pipeline.pdf",
        file_hash=file_hash,
        status="processing",
        chunking_strategy="recursive_800_160",
        metadata={"source": "watcher", "chunks_count": 3},
    )
    
    assert returned_id == doc_id
    
    # Step 2: Salva chunks direttamente nel DB (senza filesystem)
    chunks = ["DB-first chunk 1", "DB-first chunk 2", "DB-first chunk 3"]
    saved_count = await save_chunks_to_db(
        conn=mock_db_conn,
        document_id=doc_id,
        chunks=chunks,
        metadata={"file_name": "direct_pipeline.pdf"},
    )
    
    assert saved_count == 3
    
    # Verifica: nessun filesystem utilizzato, tutto DB-first
    assert mock_db_conn.fetchval.call_count == 1  # save_document_to_db
    assert mock_db_conn.executemany.call_count == 1  # save_chunks_to_db

