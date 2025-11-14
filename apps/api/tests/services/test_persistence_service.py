"""
Test suite per Conversation Persistence Service (Story 9.1).

Coverage:
- save_messages() bulk insert con idempotency
- load_session_history() con pagination
- Idempotency key generation
- Error handling graceful degradation
- Mock asyncpg pool operations

Target: 80%+ coverage
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from api.models.conversation import ConversationMessage
from api.services.persistence_service import ConversationPersistenceService


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg.Pool per unit testing."""
    pool = AsyncMock()
    
    # Mock connection context manager
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value="INSERT 0 2")  # Default success
    mock_conn.fetch = AsyncMock(return_value=[])  # Default empty result
    
    # Setup pool.acquire() context manager
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return pool, mock_conn


@pytest.fixture
def sample_messages():
    """Sample ConversationMessage list per testing."""
    return [
        ConversationMessage(
            role="user",
            content="Quali sono gli esercizi per la lombalgia?",
            timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        ),
        ConversationMessage(
            role="assistant",
            content="Gli esercizi raccomandati includono stretching e core stability...",
            timestamp=datetime(2025, 1, 15, 10, 30, 5, tzinfo=timezone.utc),
            chunk_ids=["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
        ),
    ]


class TestConversationPersistenceService:
    """Test ConversationPersistenceService functionality."""
    
    @pytest.mark.anyio
    async def test_save_messages_success(self, mock_db_pool, sample_messages):
        """Test successful row-by-row insert di messaggi."""
        pool, mock_conn = mock_db_pool
        
        # Mock execute to return INSERT result
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")
        
        service = ConversationPersistenceService(db_pool=pool)
        
        # Execute save
        result = await service.save_messages(
            session_id="session_abc123",
            messages=sample_messages,
        )
        
        # Assertions
        assert result is True
        assert mock_conn.execute.called
        
        # Verify row-by-row insert query (VALUES, no UNNEST)
        call_args_list = mock_conn.execute.call_args_list
        assert len(call_args_list) == 2  # 2 messages → 2 execute calls
        
        # Check first call
        first_call = call_args_list[0]
        query = first_call[0][0]
        assert "INSERT INTO chat_messages" in query
        assert "VALUES" in query
        assert "ON CONFLICT (idempotency_key) DO NOTHING" in query
        
        # Verify individual parameters (8 params per row)
        args = first_call[0][1:]
        assert len(args) == 8  # id, session_id, role, content, chunk_ids, metadata, created_at, idempotency_key
    
    @pytest.mark.anyio
    async def test_save_messages_empty_list(self, mock_db_pool):
        """Test save_messages con lista vuota (early return)."""
        pool, mock_conn = mock_db_pool
        service = ConversationPersistenceService(db_pool=pool)
        
        result = await service.save_messages(
            session_id="session_abc123",
            messages=[],
        )
        
        # Should return True without DB call
        assert result is True
        assert not mock_conn.execute.called
    
    @pytest.mark.anyio
    async def test_save_messages_db_error_graceful(self, mock_db_pool, sample_messages):
        """Test graceful degradation su DB error."""
        pool, mock_conn = mock_db_pool
        
        # Simulate DB error
        mock_conn.execute = AsyncMock(side_effect=Exception("DB connection failed"))
        
        service = ConversationPersistenceService(db_pool=pool)
        
        result = await service.save_messages(
            session_id="session_abc123",
            messages=sample_messages,
        )
        
        # Should return False, non-raise
        assert result is False
    
    @pytest.mark.anyio
    async def test_load_session_history_success(self, mock_db_pool):
        """Test load session history con messaggi esistenti."""
        pool, mock_conn = mock_db_pool
        
        # Mock DB rows returned
        mock_rows = [
            {
                "id": UUID("550e8400-e29b-41d4-a716-446655440000"),
                "session_id": "session_abc123",
                "role": "user",
                "content": "Domanda test",
                "source_chunk_ids": None,
                "metadata": {},
                "created_at": datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            },
            {
                "id": UUID("550e8400-e29b-41d4-a716-446655440001"),
                "session_id": "session_abc123",
                "role": "assistant",
                "content": "Risposta test",
                "source_chunk_ids": [UUID("660e8400-e29b-41d4-a716-446655440000")],
                "metadata": {},
                "created_at": datetime(2025, 1, 15, 10, 30, 5, tzinfo=timezone.utc),
            },
        ]
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        
        service = ConversationPersistenceService(db_pool=pool)
        
        messages = await service.load_session_history(
            session_id="session_abc123",
            limit=100,
            offset=0,
        )
        
        # Assertions
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Domanda test"
        assert messages[1].role == "assistant"
        assert messages[1].chunk_ids == ["660e8400-e29b-41d4-a716-446655440000"]
        
        # Verify query chiamato con correct params
        call_args = mock_conn.fetch.call_args
        query = call_args[0][0]
        assert "SELECT id, session_id, role, content" in query
        assert "FROM chat_messages" in query
        assert "WHERE session_id = $1" in query
        assert "ORDER BY created_at ASC" in query  # Default chronological
        assert "LIMIT $2 OFFSET $3" in query
    
    @pytest.mark.anyio
    async def test_load_session_history_pagination(self, mock_db_pool):
        """Test pagination parameters enforcement."""
        pool, mock_conn = mock_db_pool
        mock_conn.fetch = AsyncMock(return_value=[])
        
        service = ConversationPersistenceService(db_pool=pool)
        
        # Test limit max enforcement (600 → capped to 500)
        await service.load_session_history(
            session_id="session_abc123",
            limit=600,  # Exceeds max 500
            offset=0,
        )
        
        # Verify capped limit
        call_args = mock_conn.fetch.call_args[0]
        assert call_args[2] == 500  # limit parameter capped
    
    @pytest.mark.anyio
    async def test_load_session_history_order_desc(self, mock_db_pool):
        """Test order_desc parameter per newest first."""
        pool, mock_conn = mock_db_pool
        mock_conn.fetch = AsyncMock(return_value=[])
        
        service = ConversationPersistenceService(db_pool=pool)
        
        await service.load_session_history(
            session_id="session_abc123",
            order_desc=True,
        )
        
        # Verify DESC order in query
        call_args = mock_conn.fetch.call_args
        query = call_args[0][0]
        assert "ORDER BY created_at DESC" in query
    
    @pytest.mark.anyio
    async def test_load_session_history_empty_session(self, mock_db_pool):
        """Test load history per session senza messaggi."""
        pool, mock_conn = mock_db_pool
        mock_conn.fetch = AsyncMock(return_value=[])
        
        service = ConversationPersistenceService(db_pool=pool)
        
        messages = await service.load_session_history(
            session_id="session_nonexistent",
        )
        
        assert messages == []
    
    @pytest.mark.anyio
    async def test_load_session_history_db_error_graceful(self, mock_db_pool):
        """Test graceful degradation su DB error durante load."""
        pool, mock_conn = mock_db_pool
        mock_conn.fetch = AsyncMock(side_effect=Exception("DB query failed"))
        
        service = ConversationPersistenceService(db_pool=pool)
        
        messages = await service.load_session_history(
            session_id="session_abc123",
        )
        
        # Should return empty list, non-raise
        assert messages == []
    
    def test_generate_idempotency_key_deterministic(self, mock_db_pool):
        """Test idempotency key generation è deterministico."""
        pool, _ = mock_db_pool
        service = ConversationPersistenceService(db_pool=pool)
        
        session_id = "session_abc123"
        timestamp = datetime(2025, 1, 15, 10, 30, 0, 123000, tzinfo=timezone.utc)  # with microseconds
        content = "Test message content"
        
        # Generate key twice con same inputs
        key1 = service._generate_idempotency_key(session_id, timestamp, content)
        key2 = service._generate_idempotency_key(session_id, timestamp, content)
        
        # Should be identical (deterministic)
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
    
    def test_generate_idempotency_key_unique_per_timestamp(self, mock_db_pool):
        """Test idempotency key cambia con timestamp diverso."""
        pool, _ = mock_db_pool
        service = ConversationPersistenceService(db_pool=pool)
        
        session_id = "session_abc123"
        content = "Test message content"
        
        timestamp1 = datetime(2025, 1, 15, 10, 30, 0, 0, tzinfo=timezone.utc)
        timestamp2 = datetime(2025, 1, 15, 10, 30, 0, 1000, tzinfo=timezone.utc)  # +1ms
        
        key1 = service._generate_idempotency_key(session_id, timestamp1, content)
        key2 = service._generate_idempotency_key(session_id, timestamp2, content)
        
        # Should be different (sensitive to milliseconds)
        assert key1 != key2
    
    def test_generate_idempotency_key_unique_per_content(self, mock_db_pool):
        """Test idempotency key cambia con content diverso."""
        pool, _ = mock_db_pool
        service = ConversationPersistenceService(db_pool=pool)
        
        session_id = "session_abc123"
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        key1 = service._generate_idempotency_key(session_id, timestamp, "Content A")
        key2 = service._generate_idempotency_key(session_id, timestamp, "Content B")
        
        # Should be different
        assert key1 != key2
    
    @pytest.mark.anyio
    async def test_save_messages_converts_chunk_ids_to_uuids(self, mock_db_pool, sample_messages):
        """Test conversion chunk_ids string list → UUID[] per DB."""
        pool, mock_conn = mock_db_pool
        
        # Mock execute to return INSERT result
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")
        
        service = ConversationPersistenceService(db_pool=pool)
        
        await service.save_messages(
            session_id="session_abc123",
            messages=sample_messages,
        )
        
        # Verify chunk_ids converted to UUID list (row-by-row insert)
        call_args_list = mock_conn.execute.call_args_list
        assert len(call_args_list) == 2  # 2 messages → 2 calls
        
        # First message: no chunks → empty list (not None)
        first_call_args = call_args_list[0][0]
        chunk_ids_first = first_call_args[5]  # 5th parameter (source_chunk_ids)
        assert chunk_ids_first == []  # Always list, never None
        
        # Second message: has chunks converted to UUID list
        second_call_args = call_args_list[1][0]
        chunk_ids_second = second_call_args[5]
        assert len(chunk_ids_second) == 2
        assert isinstance(chunk_ids_second[0], UUID)

