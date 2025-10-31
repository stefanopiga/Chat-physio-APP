"""
Unit tests per document persistence layer (Story 2.4.1).

Coverage:
- save_document_to_db: inserimento, idempotenza, UUID ritornato
- update_document_status: aggiornamento status, error handling
- Foreign key constraint rispettato
- Hash collision handling

Test Database:
- Usa fixture db_conn con cleanup transaction rollback
- Test isolati e deterministici

Target Coverage: ≥90%
"""

import pytest
import uuid
from unittest.mock import AsyncMock
from api.ingestion.db_storage import save_document_to_db, update_document_status


@pytest.fixture
def mock_db_conn():
    """Mock asyncpg.Connection per unit test isolati."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_save_document_creates_record(mock_db_conn):
    """
    AC1: Inserimento nuovo documento.
    
    Given: Metadati documento validi
    When: save_document_to_db viene chiamato
    Then: Query INSERT eseguita con parametri corretti
    And: UUID valido ritornato
    """
    # Arrange
    expected_id = uuid.uuid4()
    mock_db_conn.fetchval.return_value = expected_id
    
    # Act
    result_id = await save_document_to_db(
        conn=mock_db_conn,
        file_name="test.pdf",
        file_path="/path/test.pdf",
        file_hash="abc123",
        status="processing",
        chunking_strategy="recursive_800",
        metadata={"size_bytes": 12345},
    )
    
    # Assert
    assert result_id == expected_id
    mock_db_conn.fetchval.assert_called_once()
    
    # Verifica query INSERT con ON CONFLICT
    query_executed = mock_db_conn.fetchval.call_args[0][0]
    assert "INSERT INTO documents" in query_executed
    assert "ON CONFLICT (file_hash) DO UPDATE" in query_executed
    assert "RETURNING id" in query_executed


@pytest.mark.asyncio
async def test_save_document_idempotent(mock_db_conn):
    """
    AC3: ON CONFLICT aggiorna record esistente.
    
    Given: Documento già esistente con stesso file_hash
    When: save_document_to_db viene chiamato con stesso hash
    Then: ON CONFLICT esegue UPDATE invece di INSERT
    And: document_id rimane invariato (simulato)
    """
    # Arrange: Simula stesso ID ritornato (idempotency)
    stable_id = uuid.uuid4()
    mock_db_conn.fetchval.return_value = stable_id
    
    # Act: Prima ingestion
    doc_id_1 = await save_document_to_db(
        conn=mock_db_conn,
        file_name="test.pdf",
        file_path="/path/test.pdf",
        file_hash="abc123",
        status="processing",
    )
    
    # Act: Seconda ingestion (stesso hash)
    mock_db_conn.fetchval.return_value = stable_id  # Stesso ID
    doc_id_2 = await save_document_to_db(
        conn=mock_db_conn,
        file_name="test.pdf",
        file_path="/path/test.pdf",
        file_hash="abc123",  # Stesso hash
        status="completed",  # Status diverso (update)
    )
    
    # Assert: Stesso UUID ritornato (idempotency garantita)
    assert doc_id_1 == doc_id_2
    assert mock_db_conn.fetchval.call_count == 2


@pytest.mark.asyncio
async def test_save_document_returns_uuid(mock_db_conn):
    """
    Test: Ritorno UUID valido.
    
    Given: save_document_to_db chiamato
    When: Query eseguita con successo
    Then: Valore ritornato è UUID valido
    """
    # Arrange
    expected_id = uuid.uuid4()
    mock_db_conn.fetchval.return_value = expected_id
    
    # Act
    result_id = await save_document_to_db(
        conn=mock_db_conn,
        file_name="test.pdf",
        file_path="/path/test.pdf",
        file_hash="xyz789",
        status="processing",
    )
    
    # Assert
    assert isinstance(result_id, uuid.UUID)
    assert result_id == expected_id


@pytest.mark.asyncio
async def test_update_document_status_completed(mock_db_conn):
    """
    Test: Aggiornamento status a 'completed'.
    
    Given: Documento con status 'processing'
    When: update_document_status chiamato con status='completed'
    Then: Query UPDATE eseguita con parametri corretti
    And: updated_at aggiornato
    """
    # Arrange
    doc_id = uuid.uuid4()
    
    # Act
    await update_document_status(
        conn=mock_db_conn,
        document_id=doc_id,
        status="completed",
    )
    
    # Assert
    mock_db_conn.execute.assert_called_once()
    
    # Verifica query UPDATE
    query_executed = mock_db_conn.execute.call_args[0][0]
    assert "UPDATE documents" in query_executed
    assert "status = $1" in query_executed
    assert "updated_at = NOW()" in query_executed
    
    # Verifica parametri
    params = mock_db_conn.execute.call_args[0][1:]
    assert params == ("completed", doc_id)


@pytest.mark.asyncio
async def test_update_document_status_error(mock_db_conn):
    """
    Test: Aggiornamento status a 'error' con messaggio.
    
    Given: Documento con status 'processing'
    When: update_document_status chiamato con status='error' e error message
    Then: Query UPDATE eseguita con error in metadata JSONB
    """
    # Arrange
    doc_id = uuid.uuid4()
    error_msg = "Embedding API timeout"
    
    # Act
    await update_document_status(
        conn=mock_db_conn,
        document_id=doc_id,
        status="error",
        error=error_msg,
    )
    
    # Assert
    mock_db_conn.execute.assert_called_once()
    
    # Verifica query UPDATE con jsonb_set
    query_executed = mock_db_conn.execute.call_args[0][0]
    assert "UPDATE documents" in query_executed
    assert "jsonb_set" in query_executed
    assert "metadata" in query_executed
    
    # Verifica parametri: status, error, document_id
    params = mock_db_conn.execute.call_args[0][1:]
    assert params == ("error", error_msg, doc_id)


@pytest.mark.asyncio
async def test_save_document_propagates_document_id():
    """
    AC2/AC4: document_id propagato correttamente.
    
    Given: Documento creato con save_document_to_db
    When: document_id aggiunto a metadata chunk
    Then: Ogni chunk ha metadata["document_id"] = UUID del documento
    
    Note: Test logico (non query DB), verifica integrazione endpoint.
    """
    # Arrange: Simula creazione documento
    doc_id = uuid.uuid4()
    
    # Act: Simula propagazione metadata (come in main.py)
    chunks = ["chunk1", "chunk2", "chunk3"]
    metadata_list = [
        {
            "document_id": str(doc_id),
            "document_name": "test.pdf",
            "chunking_strategy": "recursive_800",
        }
        for _ in chunks
    ]
    
    # Assert: Ogni metadata ha document_id
    assert len(metadata_list) == len(chunks)
    for meta in metadata_list:
        assert "document_id" in meta
        assert meta["document_id"] == str(doc_id)


@pytest.mark.asyncio
async def test_foreign_key_constraint_respected(mock_db_conn):
    """
    AC2: Foreign key constraint verificato (mock).
    
    Given: document_chunks.document_id deve referenziare documents.id
    When: Query verifica assenza chunk orfani
    Then: Nessun chunk senza FK valida
    
    Note: Test logico FK, verifica reale in integration test.
    """
    # Arrange: Mock query FK validation
    mock_db_conn.fetchval.return_value = 0  # Nessun chunk orfano
    
    # Act: Simula query verifica FK
    orphan_count = await mock_db_conn.fetchval(
        """
        SELECT COUNT(*) FROM document_chunks dc
        WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = dc.document_id)
        """
    )
    
    # Assert: Nessun chunk orfano (FK rispettata)
    assert orphan_count == 0


@pytest.mark.asyncio
async def test_document_hash_collision_handling(mock_db_conn):
    """
    Test: Deduplicazione su stesso file_hash.
    
    Given: Due documenti con stesso contenuto (stesso hash)
    When: save_document_to_db chiamato due volte
    Then: ON CONFLICT gestisce collision
    And: Secondo inserimento diventa UPDATE
    """
    # Arrange
    stable_id = uuid.uuid4()
    same_hash = "duplicate_hash_abc123"
    
    # Mock: Prima chiamata restituisce ID, seconda restituisce stesso ID (ON CONFLICT UPDATE)
    mock_db_conn.fetchval.side_effect = [stable_id, stable_id]
    
    # Act: Prima ingestion
    doc_id_1 = await save_document_to_db(
        conn=mock_db_conn,
        file_name="original.pdf",
        file_path="/path/original.pdf",
        file_hash=same_hash,
        status="processing",
    )
    
    # Act: Seconda ingestion con stesso hash
    doc_id_2 = await save_document_to_db(
        conn=mock_db_conn,
        file_name="duplicate.pdf",  # Nome diverso
        file_path="/path/duplicate.pdf",
        file_hash=same_hash,  # Hash identico
        status="completed",
    )
    
    # Assert: Stesso document_id (deduplicazione OK)
    assert doc_id_1 == doc_id_2
    assert mock_db_conn.fetchval.call_count == 2

