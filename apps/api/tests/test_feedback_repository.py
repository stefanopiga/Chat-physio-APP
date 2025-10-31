"""
Unit tests for FeedbackRepository - Story 4.2.4 Task 6.

Test coverage:
- T1: create_feedback_success - Feedback salvato con tutti i campi
- T2: create_feedback_upsert - Secondo feedback stesso message aggiorna (non duplica)
- T3: get_feedback_summary - Aggregazione thumbs_up/down corretta
- T4: get_feedback_by_timerange - Filtro temporale funzionante
- T5: feedback_persists_across_restarts - Simula restart con nuovo repository
- T6: create_feedback_validation_error - Vote invalido solleva ValueError
- T7: get_feedback_by_session - Filtro per session_id

Risk Mitigation Tests:
- DATA-001: T2 verifica UPSERT logic (no duplicate, update existing)
- SEC-001: RLS policies testate in integration tests (non unit test)
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from api.repositories.feedback_repository import FeedbackRepository


@pytest.fixture
def mock_supabase_client():
    """
    Mock Supabase client per unit tests isolati.
    
    Simula response structure: execute() -> APIResponse con .data attribute
    """
    client = MagicMock()
    
    # Chain: table() -> upsert() -> execute()
    table_mock = MagicMock()
    client.table.return_value = table_mock
    
    # Mock methods return self per chaining
    table_mock.upsert.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.gte.return_value = table_mock
    table_mock.lte.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.order.return_value = table_mock
    
    return client


@pytest.fixture
def sample_feedback_data():
    """Sample feedback data for tests."""
    return {
        "id": str(uuid4()),
        "session_id": str(uuid4()),
        "message_id": str(uuid4()),
        "vote": "up",
        "comment": "Great answer!",
        "user_id": str(uuid4()),
        "ip_address": "192.168.1.1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


# ==============================================================================
# T1: create_feedback_success
# ==============================================================================

@pytest.mark.asyncio
async def test_create_feedback_success(mock_supabase_client, sample_feedback_data):
    """
    T1: Verify feedback is successfully created with all fields.
    
    Validates:
    - Repository calls Supabase table('feedback').upsert()
    - All fields are passed correctly
    - Response is returned from execute().data
    """
    # Arrange
    mock_response = MagicMock()
    mock_response.data = [sample_feedback_data]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act
    result = await repo.create_feedback(
        session_id=sample_feedback_data["session_id"],
        message_id=sample_feedback_data["message_id"],
        vote="up",
        comment="Great answer!",
        user_id=sample_feedback_data["user_id"],
        ip_address="192.168.1.1"
    )
    
    # Assert
    assert result["id"] == sample_feedback_data["id"]
    assert result["vote"] == "up"
    assert result["comment"] == "Great answer!"
    
    # Verify Supabase calls
    mock_supabase_client.table.assert_called_once_with("feedback")
    upsert_call = mock_supabase_client.table.return_value.upsert
    assert upsert_call.called
    
    # Verify payload structure
    payload = upsert_call.call_args[0][0]
    assert payload["session_id"] == sample_feedback_data["session_id"]
    assert payload["message_id"] == sample_feedback_data["message_id"]
    assert payload["vote"] == "up"
    assert payload["comment"] == "Great answer!"


# ==============================================================================
# T2: create_feedback_upsert (DATA-001 Risk Mitigation)
# ==============================================================================

@pytest.mark.asyncio
async def test_create_feedback_upsert(mock_supabase_client, sample_feedback_data):
    """
    T2: Verify UPSERT logic - second feedback on same message updates existing.
    
    Risk: DATA-001 - Duplicate feedback prevention
    
    Validates:
    - on_conflict parameter is set to "session_id,message_id"
    - Second submission updates vote instead of creating duplicate
    """
    # Arrange - First feedback
    feedback_v1 = sample_feedback_data.copy()
    feedback_v1["vote"] = "up"
    mock_response_v1 = MagicMock()
    mock_response_v1.data = [feedback_v1]
    
    # Second feedback (same session+message, different vote)
    feedback_v2 = sample_feedback_data.copy()
    feedback_v2["vote"] = "down"
    feedback_v2["updated_at"] = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
    mock_response_v2 = MagicMock()
    mock_response_v2.data = [feedback_v2]
    
    # Mock returns different responses on successive calls
    mock_supabase_client.table.return_value.upsert.return_value.execute.side_effect = [
        mock_response_v1,
        mock_response_v2
    ]
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act - Submit feedback twice
    result1 = await repo.create_feedback(
        session_id=sample_feedback_data["session_id"],
        message_id=sample_feedback_data["message_id"],
        vote="up"
    )
    
    result2 = await repo.create_feedback(
        session_id=sample_feedback_data["session_id"],
        message_id=sample_feedback_data["message_id"],
        vote="down"
    )
    
    # Assert
    assert result1["vote"] == "up"
    assert result2["vote"] == "down"
    
    # Verify UPSERT was called twice with correct on_conflict
    assert mock_supabase_client.table.return_value.upsert.call_count == 2
    
    for call in mock_supabase_client.table.return_value.upsert.call_args_list:
        _, kwargs = call
        assert kwargs.get("on_conflict") == "session_id,message_id"


# ==============================================================================
# T3: get_feedback_summary
# ==============================================================================

@pytest.mark.asyncio
async def test_get_feedback_summary(mock_supabase_client):
    """
    T3: Verify feedback summary aggregates thumbs up/down correctly.
    
    Validates:
    - Aggregation logic counts votes correctly
    - Returns structure: {thumbs_up, thumbs_down, total}
    """
    # Arrange - Mock feedback data with mixed votes
    feedback_data = [
        {"vote": "up"},
        {"vote": "up"},
        {"vote": "up"},
        {"vote": "down"},
        {"vote": "down"},
    ]
    
    mock_response = MagicMock()
    mock_response.data = feedback_data
    mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act
    summary = await repo.get_feedback_summary()
    
    # Assert
    assert summary["thumbs_up"] == 3
    assert summary["thumbs_down"] == 2
    assert summary["total"] == 5
    
    # Verify query called select("vote") for minimal data transfer
    mock_supabase_client.table.return_value.select.assert_called_once_with("vote")


# ==============================================================================
# T4: get_feedback_by_timerange
# ==============================================================================

@pytest.mark.asyncio
async def test_get_feedback_by_timerange(mock_supabase_client, sample_feedback_data):
    """
    T4: Verify time-range filtering for temporal analytics.
    
    Validates:
    - gte() and lte() filters applied correctly
    - Defaults end_date to NOW() if not provided
    - Returns feedback within range
    """
    # Arrange
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    
    feedback_in_range = [
        sample_feedback_data.copy(),
        {**sample_feedback_data, "id": str(uuid4()), "created_at": cutoff.isoformat()}
    ]
    
    mock_response = MagicMock()
    mock_response.data = feedback_in_range
    mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.return_value.order.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act
    result = await repo.get_feedback_by_timerange(start_date=cutoff)
    
    # Assert
    assert len(result) == 2
    assert result[0]["id"] == sample_feedback_data["id"]
    
    # Verify range filters called
    mock_supabase_client.table.return_value.select.return_value.gte.assert_called_once()
    mock_supabase_client.table.return_value.select.return_value.gte.return_value.lte.assert_called_once()


# ==============================================================================
# T5: feedback_persists_across_restarts
# ==============================================================================

@pytest.mark.asyncio
async def test_feedback_persists_across_restarts(mock_supabase_client, sample_feedback_data):
    """
    T5: Simulate app restart - new repository instance still reads persisted data.
    
    Validates:
    - Data persisted in Supabase survives repository recreation
    - No in-memory state dependency (unlike old feedback_store)
    """
    # Arrange - Mock existing feedback in DB
    mock_response = MagicMock()
    mock_response.data = [sample_feedback_data]
    mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response
    
    # Act - Create first repository, "crash", create second repository
    repo1 = FeedbackRepository(mock_supabase_client)
    summary1 = await repo1.get_feedback_summary()
    
    # Simulate restart: new repository instance
    repo2 = FeedbackRepository(mock_supabase_client)
    summary2 = await repo2.get_feedback_summary()
    
    # Assert - Data still accessible after "restart"
    assert summary1["total"] == summary2["total"]
    assert summary1["thumbs_up"] == summary2["thumbs_up"]


# ==============================================================================
# T6: create_feedback_validation_error
# ==============================================================================

@pytest.mark.asyncio
async def test_create_feedback_validation_error(mock_supabase_client, sample_feedback_data):
    """
    T6: Verify invalid vote value raises ValueError before DB call.
    
    Validates:
    - Client-side validation prevents invalid data reaching DB
    - Error message is descriptive
    """
    # Arrange
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act & Assert
    with pytest.raises(ValueError, match="Invalid vote value.*Must be 'up' or 'down'"):
        await repo.create_feedback(
            session_id=sample_feedback_data["session_id"],
            message_id=sample_feedback_data["message_id"],
            vote="invalid_vote"  # Invalid
        )
    
    # Verify Supabase client was NOT called
    mock_supabase_client.table.assert_not_called()


# ==============================================================================
# T7: get_feedback_by_session
# ==============================================================================

@pytest.mark.asyncio
async def test_get_feedback_by_session(mock_supabase_client, sample_feedback_data):
    """
    T7: Verify session-based feedback filtering.
    
    Validates:
    - eq() filter on session_id works correctly
    - Returns feedback for specific session only
    """
    # Arrange
    session_id = sample_feedback_data["session_id"]
    feedback_for_session = [sample_feedback_data, {**sample_feedback_data, "id": str(uuid4())}]
    
    mock_response = MagicMock()
    mock_response.data = feedback_for_session
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Act
    result = await repo.get_feedback_by_session(session_id)
    
    # Assert
    assert len(result) == 2
    assert all(f["session_id"] == session_id for f in result)
    
    # Verify eq filter called with session_id
    mock_supabase_client.table.return_value.select.return_value.eq.assert_called_once_with("session_id", session_id)


# ==============================================================================
# Edge Case Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_create_feedback_with_uuid_objects(mock_supabase_client):
    """Verify repository handles UUID objects (converts to strings)."""
    session_uuid = uuid4()
    message_uuid = uuid4()
    user_uuid = uuid4()
    
    mock_response = MagicMock()
    mock_response.data = [{"id": str(uuid4()), "vote": "up"}]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    # Should not raise - UUID objects converted to strings
    result = await repo.create_feedback(
        session_id=session_uuid,
        message_id=message_uuid,
        vote="up",
        user_id=user_uuid
    )
    
    assert result["vote"] == "up"


@pytest.mark.asyncio
async def test_get_feedback_summary_empty_db(mock_supabase_client):
    """Verify summary returns zeros when no feedback exists."""
    mock_response = MagicMock()
    mock_response.data = []  # Empty DB
    mock_supabase_client.table.return_value.select.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    summary = await repo.get_feedback_summary()
    
    assert summary["thumbs_up"] == 0
    assert summary["thumbs_down"] == 0
    assert summary["total"] == 0


@pytest.mark.asyncio
async def test_create_feedback_anonymous_user(mock_supabase_client):
    """Verify feedback creation works with NULL user_id (anonymous students)."""
    mock_response = MagicMock()
    mock_response.data = [{"id": str(uuid4()), "vote": "up", "user_id": None}]
    mock_supabase_client.table.return_value.upsert.return_value.execute.return_value = mock_response
    
    repo = FeedbackRepository(mock_supabase_client)
    
    result = await repo.create_feedback(
        session_id=str(uuid4()),
        message_id=str(uuid4()),
        vote="up",
        user_id=None  # Anonymous
    )
    
    assert result["user_id"] is None

