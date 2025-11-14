"""
Integration tests per HybridConversationManager (Story 9.1).

Tests:
- Task 5: Graceful degradation con DB unavailable
- Task 7: Integration testing E2E con dual-write
- Task 8: Durable outbox pattern con retry logic

Coverage target: 80%+
"""
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import pytest

from api.models.conversation import ConversationMessage
from api.services.conversation_service import (
    HybridConversationManager,
    CircuitBreaker,
    CircuitBreakerOpenError,
)
from api.services.persistence_service import ConversationPersistenceService
from api.services.outbox_queue import OutboxPersistenceQueue
from api.utils.metrics import metrics


@pytest.fixture
def mock_db_pool():
    """Mock asyncpg pool con async context manager corretto."""
    pool = Mock()
    
    # Configure acquire() per ritornare async context manager
    async def mock_acquire():
        mock_conn = AsyncMock()
        return mock_conn
    
    # Make acquire() return async context manager
    pool.acquire = Mock(return_value=AsyncMock())
    pool.acquire.return_value.__aenter__ = AsyncMock()
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    
    return pool


@pytest.fixture
def persistence_service(mock_db_pool):
    """ConversationPersistenceService con mock pool."""
    return ConversationPersistenceService(mock_db_pool)


@pytest.fixture
def outbox_queue(tmp_path):
    """OutboxPersistenceQueue con temp directory."""
    outbox_path = tmp_path / "test_outbox.jsonl"
    dlq_path = tmp_path / "test_dlq.jsonl"
    return OutboxPersistenceQueue(
        outbox_path=str(outbox_path),
        dlq_path=str(dlq_path),
        max_retries=3,  # Ridotto per test rapidi
    )


@pytest.fixture
def hybrid_manager(persistence_service, outbox_queue):
    """HybridConversationManager test instance."""
    manager = HybridConversationManager(
        persistence_service=persistence_service,
        enable_persistence=True,
        outbox_queue=outbox_queue,
        max_turns=3,
        max_tokens=2000,
        compact_length=150,
    )
    # Reset metrics per test isolation
    metrics.reset()
    return manager


# ============================================
# Task 5: Graceful Degradation Tests
# ============================================


@pytest.mark.anyio
async def test_graceful_degradation_db_unavailable(hybrid_manager, mock_db_pool):
    """
    Test graceful degradation: DB unavailable → continua con L1 cache only.
    
    Story 9.1 AC6, Task 5.4: Verify chat continua anche se DB unavailable.
    """
    # Simulate DB unavailable
    mock_db_pool.acquire.side_effect = Exception("DB connection failed")
    
    # Add turn deve succedere (L1 cache sempre funziona)
    hybrid_manager.add_turn(
        session_id="test_session",
        user_message="Test question",
        assistant_message="Test answer",
        chunk_ids=["chunk1"],
    )
    
    # Verify L1 cache write succeeded
    context_window = hybrid_manager.get_context_window("test_session")
    assert len(context_window.messages) == 2
    assert context_window.messages[0].content == "Test question"
    assert context_window.messages[1].content == "Test answer"
    
    # Wait async write attempt
    await asyncio.sleep(0.1)
    
    # Verify metrics logged failure
    assert metrics.get_counter("db_writes_failed") > 0


@pytest.mark.anyio
async def test_graceful_degradation_circuit_breaker_open(hybrid_manager):
    """
    Test graceful degradation: Circuit breaker OPEN → fallback outbox.
    
    Story 9.1 AC2, Task 3.12: Circuit breaker protegge DB da overload.
    """
    # Simulate 3 consecutive failures per trip circuit breaker
    with patch.object(
        hybrid_manager.persistence,
        "save_messages",
        side_effect=Exception("DB error"),
    ):
        for i in range(3):
            hybrid_manager.add_turn(
                session_id=f"session_{i}",
                user_message=f"Question {i}",
                assistant_message=f"Answer {i}",
            )
            await asyncio.sleep(0.1)
    
    # Circuit breaker should be OPEN
    assert hybrid_manager.circuit_breaker.state == "OPEN"
    assert metrics.get_gauge("circuit_breaker_open") == 1
    
    # Verify outbox has entries
    assert Path(hybrid_manager.outbox_queue.outbox_path).exists()


@pytest.mark.anyio
async def test_feature_flag_disabled_fallback(mock_db_pool):
    """
    Test feature flag OFF: HybridManager con enable_persistence=False.
    
    Story 9.1 AC3, Task 4.4: Verify backward compatibility Story 7.1.
    """
    # Initialize with persistence disabled
    manager = HybridConversationManager(
        persistence_service=None,
        enable_persistence=False,
        max_turns=3,
    )
    
    # Reset metrics per test isolation
    metrics.reset()
    
    # Add turn should succeed (L1 only) - unique session
    session_id = "test_flag_disabled_session"
    manager.add_turn(
        session_id=session_id,
        user_message="Test",
        assistant_message="Answer",
    )
    
    # Verify L1 cache works
    context_window = manager.get_context_window(session_id)
    assert len(context_window.messages) == 2
    
    # No async writes attempted (persistence disabled)
    await asyncio.sleep(0.1)
    assert metrics.get_counter("db_writes_succeeded") == 0


# ============================================
# Task 7: Integration Testing E2E
# ============================================


@pytest.mark.anyio
async def test_dual_write_integration_e2e(hybrid_manager, mock_db_pool):
    """
    Test dual-write E2E: L1 cache + L2 DB persistence.
    
    Story 9.1 AC1, AC2, Task 7.1: Full flow add_turn → async persist → verify DB.
    """
    # Mock successful DB write
    async def mock_execute(query, *args):
        return "INSERT 0 2"
    
    mock_conn = AsyncMock()
    mock_conn.execute = mock_execute
    
    # Fix: Configure acquire() to return async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_db_pool.acquire.return_value = mock_context
    
    # Add turn (unique session per test isolation)
    session_id = "test_dual_write_session"
    hybrid_manager.add_turn(
        session_id=session_id,
        user_message="How does muscle contraction work?",
        assistant_message="Muscle contraction involves actin-myosin interaction...",
        chunk_ids=["chunk_123"],
    )
    
    # Verify L1 cache immediate
    context_window = hybrid_manager.get_context_window(session_id)
    assert len(context_window.messages) == 2
    assert context_window.total_tokens > 0
    
    # Wait async DB write
    await asyncio.sleep(0.2)
    
    # Verify metrics
    assert metrics.get_counter("db_writes_succeeded") == 1
    assert metrics.get_counter("cache_hits") >= 1
    histogram_stats = metrics.get_histogram_stats("db_write_latency_ms")
    assert histogram_stats["count"] == 1
    assert histogram_stats["p95"] < 1000  # <1s


@pytest.mark.anyio
async def test_backpressure_drop_oldest(hybrid_manager):
    """
    Test backpressure: queue depth >100 → drop oldest task.
    
    Story 9.1 AC2, Task 3.11: Verify bounded queue protegge memory.
    """
    # Mock slow DB writes
    async def slow_write(*args, **kwargs):
        await asyncio.sleep(1)
        return True
    
    with patch.object(hybrid_manager.persistence, "save_messages", side_effect=slow_write):
        # Enqueue 105 tasks rapidamente
        for i in range(105):
            hybrid_manager.add_turn(
                session_id=f"session_{i}",
                user_message=f"Question {i}",
                assistant_message=f"Answer {i}",
            )
        
        # Verify backpressure activated
        assert metrics.get_counter("backpressure_activated") >= 5  # Dropped at least 5


@pytest.mark.anyio
async def test_performance_db_write_latency_p95(hybrid_manager, mock_db_pool):
    """
    Test performance: DB write latency p95 <100ms.
    
    Story 9.1 AC7, Task 7.5: Performance requirement verificato.
    """
    # Mock fast DB writes
    async def fast_write(query, *args):
        await asyncio.sleep(0.05)  # 50ms simulated latency
        return "INSERT 0 2"
    
    mock_conn = AsyncMock()
    mock_conn.execute = fast_write
    
    # Fix: Configure acquire() to return async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_conn
    mock_context.__aexit__.return_value = None
    mock_db_pool.acquire.return_value = mock_context
    
    # Execute 10 writes
    for i in range(10):
        hybrid_manager.add_turn(
            session_id=f"session_{i}",
            user_message=f"Q{i}",
            assistant_message=f"A{i}",
        )
    
    # Wait all writes
    await asyncio.sleep(1)
    
    # Verify p95 latency <100ms
    histogram_stats = metrics.get_histogram_stats("db_write_latency_ms")
    assert histogram_stats["count"] == 10
    assert histogram_stats["p95"] < 100


# ============================================
# Task 8: Durable Outbox Pattern Tests
# ============================================


@pytest.mark.anyio
async def test_outbox_append_on_db_failure(hybrid_manager, outbox_queue):
    """
    Test outbox append: DB failure → append to outbox.
    
    Story 9.1 AC9, Task 8.8: Verify fallback to outbox on DB error.
    """
    # Simulate DB failure
    with patch.object(
        hybrid_manager.persistence,
        "save_messages",
        side_effect=Exception("DB unavailable"),
    ):
        hybrid_manager.add_turn(
            session_id="test_session",
            user_message="Test question",
            assistant_message="Test answer",
        )
        
        # Wait async attempt
        await asyncio.sleep(0.2)
    
    # Verify outbox has entry
    outbox_path = Path(outbox_queue.outbox_path)
    assert outbox_path.exists()
    
    with open(outbox_path, "r") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    import json
    entry = json.loads(lines[0])
    assert entry["session_id"] == "test_session"
    assert entry["retry_count"] == 0


@pytest.mark.anyio
async def test_outbox_idempotency_key_generation(outbox_queue):
    """
    Test idempotency: same messages → same key.
    
    Story 9.1 AC9, Task 8.7: Verify deterministico idempotency key.
    """
    timestamp = datetime.now(timezone.utc)
    messages = [
        ConversationMessage(
            role="user",
            content="Test question",
            timestamp=timestamp,
        )
    ]
    
    key1 = outbox_queue._generate_idempotency_key("session_1", messages)
    key2 = outbox_queue._generate_idempotency_key("session_1", messages)
    
    # Same input → same key
    assert key1 == key2
    
    # Different session → different key
    key3 = outbox_queue._generate_idempotency_key("session_2", messages)
    assert key1 != key3


@pytest.mark.anyio
async def test_outbox_retry_success(outbox_queue, persistence_service, mock_db_pool):
    """
    Test outbox retry: success → remove from outbox.
    
    Story 9.1 AC9, Task 8.8: Verify eventual consistency on DB recovery.
    """
    # Create outbox entry (use old timestamp per bypass backoff)
    import time
    old_timestamp = datetime.fromtimestamp(time.time() - 5, tz=timezone.utc)
    
    messages = [
        ConversationMessage(
            role="user",
            content="Test",
            timestamp=old_timestamp,
        )
    ]
    await outbox_queue.append("session_test", messages)
    
    # Modify entry timestamp per bypass backoff (simulate old entry)
    import json
    with open(outbox_queue.outbox_path, "r") as f:
        line = f.readline()
    entry = json.loads(line)
    entry["timestamp"] = old_timestamp.isoformat()
    with open(outbox_queue.outbox_path, "w") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Mock successful DB write - must mock persistence_service.save_messages as async
    async def mock_save_success(*args, **kwargs):
        return True
    
    persistence_service.save_messages = mock_save_success
    
    # Retry pending
    await outbox_queue.retry_pending(persistence_service)
    
    # Verify outbox cleared (success)
    with open(outbox_queue.outbox_path, "r") as f:
        content = f.read()
    
    # Debug: se non è vuoto, print remaining content
    if content.strip():
        print(f"DEBUG: Outbox non vuoto dopo retry: {content}")
    
    assert content.strip() == ""


@pytest.mark.anyio
async def test_outbox_retry_exponential_backoff(outbox_queue, persistence_service):
    """
    Test exponential backoff: retry_count increases delay.
    
    Story 9.1 AC9, Task 8.4: Verify backoff 1s→2s→4s→8s→60s max.
    """
    # Create entry con retry_count=2
    import json
    entry = {
        "id": "test_id",
        "session_id": "session_test",
        "messages": [{"role": "user", "content": "Test", "timestamp": datetime.now(timezone.utc).isoformat()}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "retry_count": 2,
        "first_failure_at": datetime.now(timezone.utc).isoformat(),
    }
    
    with open(outbox_queue.outbox_path, "w") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Mock DB failure
    with patch.object(persistence_service, "save_messages", return_value=False):
        # Retry immediately (should skip due to backoff)
        await outbox_queue.retry_pending(persistence_service)
    
    # Verify entry still pending (backoff prevented retry)
    with open(outbox_queue.outbox_path, "r") as f:
        lines = f.readlines()
    
    assert len(lines) == 1


@pytest.mark.anyio
async def test_outbox_dead_letter_queue_after_max_retries(outbox_queue, persistence_service):
    """
    Test DLQ: retry_count >= 3 → move to DLQ.
    
    Story 9.1 AC9, Task 8.9: Verify DLQ per failures >max_retries.
    """
    # Create entry con retry_count=3 (max)
    import json
    import time
    
    # Set timestamp old enough per bypass backoff
    old_timestamp = datetime.fromtimestamp(time.time() - 100, tz=timezone.utc).isoformat()
    
    entry = {
        "id": "test_id",
        "session_id": "session_test",
        "messages": [{"role": "user", "content": "Test", "timestamp": datetime.now(timezone.utc).isoformat()}],
        "timestamp": old_timestamp,
        "retry_count": 2,  # Will become 3 after retry failure
        "first_failure_at": old_timestamp,
    }
    
    with open(outbox_queue.outbox_path, "w") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Mock DB failure
    with patch.object(persistence_service, "save_messages", side_effect=Exception("DB error")):
        await outbox_queue.retry_pending(persistence_service)
    
    # Verify moved to DLQ
    assert Path(outbox_queue.dlq_path).exists()
    
    with open(outbox_queue.dlq_path, "r") as f:
        dlq_lines = f.readlines()
    
    assert len(dlq_lines) == 1
    dlq_entry = json.loads(dlq_lines[0])
    assert dlq_entry["session_id"] == "session_test"
    assert dlq_entry["retry_count"] == 3


# ============================================
# Circuit Breaker Unit Tests
# ============================================


@pytest.mark.anyio
async def test_circuit_breaker_transitions():
    """
    Test circuit breaker state transitions.
    
    Story 9.1 Task 3.12: CLOSED → OPEN → HALF_OPEN → CLOSED.
    """
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    
    # Initial state: CLOSED
    assert cb.state == "CLOSED"
    
    # Simulate 2 failures → OPEN
    async def failing_func():
        raise Exception("Test error")
    
    for _ in range(2):
        with pytest.raises(Exception):
            await cb.call(failing_func)
    
    assert cb.state == "OPEN"
    
    # Immediate call should fail fast
    with pytest.raises(CircuitBreakerOpenError):
        await cb.call(failing_func)
    
    # Wait timeout → HALF_OPEN
    await asyncio.sleep(1.1)
    
    # Success call → CLOSED
    async def success_func():
        return "OK"
    
    result = await cb.call(success_func)
    assert result == "OK"
    assert cb.state == "CLOSED"

