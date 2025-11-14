"""
Unit tests per GET /api/v1/chat/sessions/{sessionId}/history/full endpoint.

Story 9.2 Task 1.5: Backend endpoint testing con mock persistence service.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from api.models.conversation import ConversationMessage


def test_get_session_history_success(client_student):
    """Test endpoint ritorna history con success."""
    # Mock persistence service
    mock_messages = [
        ConversationMessage(
            role="user",
            content="Domanda test",
            timestamp=datetime(2025, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
            chunk_ids=None,
        ),
        ConversationMessage(
            role="assistant",
            content="Risposta test",
            timestamp=datetime(2025, 1, 12, 10, 0, 1, tzinfo=timezone.utc),
            chunk_ids=["chunk-id-1", "chunk-id-2"],
        ),
    ]
    
    with patch("api.routers.chat.db_pool") as mock_db_pool, \
         patch("api.routers.chat.ConversationPersistenceService") as mock_service_class:
        
        mock_db_pool.__bool__.return_value = True
        mock_service = AsyncMock()
        mock_service.load_session_history = AsyncMock(return_value=mock_messages)
        mock_service_class.return_value = mock_service
        
        response = client_student.get(
            "/api/v1/chat/sessions/test-session-id/history/full?limit=100&offset=0"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["total_count"] == 2
        assert data["has_more"] is False
        
        # Verify message structure
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Domanda test"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][1]["source_chunk_ids"] == ["chunk-id-1", "chunk-id-2"]


def test_get_session_history_empty_404(client_student):
    """Test endpoint ritorna 404 per sessione nuova."""
    with patch("api.routers.chat.db_pool") as mock_db_pool, \
         patch("api.routers.chat.ConversationPersistenceService") as mock_service_class:
        
        mock_db_pool.__bool__.return_value = True
        mock_service = AsyncMock()
        mock_service.load_session_history = AsyncMock(return_value=[])
        mock_service_class.return_value = mock_service
        
        response = client_student.get(
            "/api/v1/chat/sessions/new-session/history/full"
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Session history not found" in data["detail"]


def test_get_session_history_unauthorized(client_no_auth):
    """Test endpoint ritorna 401 senza JWT."""
    response = client_no_auth.get(
        "/api/v1/chat/sessions/test/history/full"
    )
    
    assert response.status_code == 401


def test_get_session_history_pagination_has_more(client_student):
    """Test endpoint pagination con has_more=True."""
    # Create 101 messages per testare pagination (fix timestamp seconds)
    mock_messages = [
        ConversationMessage(
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}",
            timestamp=datetime(2025, 1, 12, 10, i // 60, i % 60, tzinfo=timezone.utc),
            chunk_ids=None,
        )
        for i in range(101)
    ]
    
    with patch("api.routers.chat.db_pool") as mock_db_pool, \
         patch("api.routers.chat.ConversationPersistenceService") as mock_service_class:
        
        mock_db_pool.__bool__.return_value = True
        mock_service = AsyncMock()
        mock_service.load_session_history = AsyncMock(return_value=mock_messages)
        mock_service_class.return_value = mock_service
        
        response = client_student.get(
            "/api/v1/chat/sessions/test-session/history/full?limit=100&offset=0"
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return 100 messages (limit)
        assert len(data["messages"]) == 100
        # has_more should be True perché abbiamo 101 messaggi
        assert data["has_more"] is True
        assert data["total_count"] >= 100


def test_get_session_history_feature_flag_disabled(client_student):
    """Test graceful degradation quando feature flag disabled."""
    with patch("api.routers.chat.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.enable_persistent_memory = False
        mock_get_settings.return_value = mock_settings
        
        response = client_student.get(
            "/api/v1/chat/sessions/test-session/history/full"
        )
        
        # Should return empty history without error
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total_count"] == 0
        assert data["has_more"] is False


def test_get_session_history_db_pool_unavailable(client_student):
    """Test graceful degradation quando db_pool unavailable."""
    with patch("api.routers.chat.db_pool", None):
        response = client_student.get(
            "/api/v1/chat/sessions/test-session/history/full"
        )
        
        # Should return empty history without error
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total_count"] == 0
        assert data["has_more"] is False


def test_get_session_history_persistence_error(client_student):
    """Test error handling quando persistence service fails."""
    with patch("api.routers.chat.db_pool") as mock_db_pool, \
         patch("api.routers.chat.ConversationPersistenceService") as mock_service_class:
        
        mock_db_pool.__bool__.return_value = True
        mock_service = AsyncMock()
        mock_service.load_session_history = AsyncMock(
            side_effect=Exception("Database connection error")
        )
        mock_service_class.return_value = mock_service
        
        response = client_student.get(
            "/api/v1/chat/sessions/test-session/history/full"
        )
        
        # Should return 500 error
        assert response.status_code == 500
        data = response.json()
        assert "Failed to load session history" in data["detail"]


def test_get_session_history_rate_limit_exceeded(client_student):
    """Test endpoint ritorna 429 quando rate limit superato con Retry-After header."""
    with patch("api.routers.chat.rate_limit_service") as mock_rate_limit:
        # Mock rate limit service per simulare 429 Too Many Requests
        from fastapi import HTTPException
        mock_rate_limit.enforce_rate_limit.side_effect = HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": "60"}
        )
        
        response = client_student.get(
            "/api/v1/chat/sessions/test-session/history/full"
        )
        
        # Should return 429 with Retry-After header
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"
        data = response.json()
        assert "Rate limit exceeded" in data["detail"]
