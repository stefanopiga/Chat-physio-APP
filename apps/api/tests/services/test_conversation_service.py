"""
Test suite per Conversation Manager Service (Story 7.1).

Coverage:
- Context window loading (sliding window)
- Token counting (tiktoken + fallback)
- Token budget truncation
- Message formatting per prompt
- Turn persistence
"""
import pytest
from datetime import datetime, timezone

from api.models.conversation import ConversationMessage, ChatContextWindow
from api.services.conversation_service import (
    ConversationManager,
    get_conversation_manager,
    reset_conversation_manager,
)
from api.stores import chat_messages_store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset chat_messages_store before each test."""
    chat_messages_store.clear()
    reset_conversation_manager()
    yield
    chat_messages_store.clear()
    reset_conversation_manager()


class TestConversationManager:
    """Test ConversationManager functionality."""
    
    def test_get_context_window_empty(self):
        """Test loading context window for session without messages."""
        manager = ConversationManager()
        window = manager.get_context_window("session_123")
        
        assert window.session_id == "session_123"
        assert len(window.messages) == 0
        assert window.total_tokens == 0
    
    def test_get_context_window_with_messages(self):
        """Test loading context window with existing messages."""
        session_id = "session_123"
        
        # Populate store with 4 messages (2 turns)
        chat_messages_store[session_id] = [
            {
                "id": "msg_1",
                "role": "user",
                "content": "Cos'è la spondilolistesi?",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "msg_2",
                "role": "assistant",
                "content": "La spondilolistesi è una condizione...",
                "citations": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "msg_3",
                "role": "user",
                "content": "Quali sono i gradi?",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "msg_4",
                "role": "assistant",
                "content": "Si classifica secondo Meyerding in gradi I-IV...",
                "citations": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        
        manager = ConversationManager()
        window = manager.get_context_window(session_id)
        
        assert window.session_id == session_id
        assert len(window.messages) == 4
        assert window.messages[0].role == "user"
        assert window.messages[1].role == "assistant"
        assert window.total_tokens > 0
    
    def test_sliding_window_max_turns(self):
        """Test sliding window keeps only last MAX_TURNS * 2 messages."""
        session_id = "session_123"
        
        # Populate store with 10 messages (5 turns) - exceeds MAX_TURNS (3)
        messages = []
        for i in range(10):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({
                "id": f"msg_{i}",
                "role": role,
                "content": f"Message {i}",
                "citations": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        chat_messages_store[session_id] = messages
        
        manager = ConversationManager(max_turns=3)
        window = manager.get_context_window(session_id)
        
        # Should keep last 6 messages (3 turns * 2)
        assert len(window.messages) == 6
        assert window.messages[0].content == "Message 4"  # oldest kept
        assert window.messages[-1].content == "Message 9"  # newest
    
    def test_add_turn(self):
        """Test adding conversation turn persists correctly."""
        session_id = "session_456"
        manager = ConversationManager()
        
        manager.add_turn(
            session_id,
            "Cos'è la stenosi spinale?",
            "La stenosi spinale è un restringimento...",
            ["chunk_1", "chunk_2"],
        )
        
        # Verify stored in chat_messages_store
        stored = chat_messages_store.get(session_id)
        assert stored is not None
        assert len(stored) == 2  # user + assistant
        
        assert stored[0]["role"] == "user"
        assert stored[0]["content"] == "Cos'è la stenosi spinale?"
        
        assert stored[1]["role"] == "assistant"
        assert stored[1]["content"] == "La stenosi spinale è un restringimento..."
        assert len(stored[1]["citations"]) == 2
    
    def test_format_for_prompt_empty(self):
        """Test formatting empty context window for prompt."""
        manager = ConversationManager()
        window = ChatContextWindow(session_id="test", messages=[])
        
        formatted = manager.format_for_prompt(window)
        
        assert "PRIMA INTERAZIONE" in formatted
        assert "nessuna cronologia" in formatted
    
    def test_format_for_prompt_with_messages(self):
        """Test formatting context window with messages."""
        manager = ConversationManager()
        messages = [
            ConversationMessage(
                role="user",
                content="Domanda 1",
                timestamp=datetime.now(timezone.utc),
            ),
            ConversationMessage(
                role="assistant",
                content="Risposta 1",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        window = ChatContextWindow(session_id="test", messages=messages, total_tokens=50)
        
        formatted = manager.format_for_prompt(window)
        
        assert "CRONOLOGIA CONVERSAZIONE" in formatted
        assert "STUDENTE: Domanda 1" in formatted
        assert "TUTOR: Risposta 1" in formatted
        assert "ISTRUZIONI CONTESTUALI" in formatted
    
    def test_format_for_prompt_compacts_old_messages(self):
        """Test older messages are compacted in prompt formatting."""
        manager = ConversationManager(compact_length=20)
        
        long_content = "A" * 100  # Long message
        messages = [
            ConversationMessage(role="user", content=long_content, timestamp=datetime.now(timezone.utc)),
            ConversationMessage(role="assistant", content="Old response", timestamp=datetime.now(timezone.utc)),
            ConversationMessage(role="user", content="Recent question", timestamp=datetime.now(timezone.utc)),
            ConversationMessage(role="assistant", content="Recent response", timestamp=datetime.now(timezone.utc)),
        ]
        window = ChatContextWindow(session_id="test", messages=messages, total_tokens=200)
        
        formatted = manager.format_for_prompt(window)
        
        # Old message should be compacted (truncated)
        assert "..." in formatted  # Indicates truncation
        # Recent messages should be full
        assert "Recent question" in formatted
        assert "Recent response" in formatted
    
    def test_token_counting(self):
        """Test token counting (fallback if tiktoken unavailable)."""
        manager = ConversationManager()
        messages = [
            ConversationMessage(role="user", content="Short", timestamp=datetime.now(timezone.utc)),
            ConversationMessage(role="assistant", content="Another short message", timestamp=datetime.now(timezone.utc)),
        ]
        
        token_count = manager._count_tokens(messages)
        
        # Should return some positive count
        assert token_count > 0
    
    def test_token_budget_truncation(self):
        """Test truncation when messages exceed token budget."""
        manager = ConversationManager(max_tokens=500)  # Realistic budget
        
        # Create messages that will exceed budget
        messages = []
        for i in range(8):
            role = "user" if i % 2 == 0 else "assistant"
            # Long content to ensure token budget exceeded
            content = "This is a long message with many words " * 10
            messages.append(
                ConversationMessage(role=role, content=content, timestamp=datetime.now(timezone.utc))
            )
        
        truncated = manager._truncate_to_budget(messages)
        
        # Should have removed oldest messages
        assert len(truncated) < len(messages)
        assert len(truncated) >= 2  # Always keep at least last turn
        
        # Verify token count is reduced (may not be exactly under budget if last turn is large)
        original_count = manager._count_tokens(messages)
        truncated_count = manager._count_tokens(truncated)
        assert truncated_count < original_count  # Reduced tokens


class TestConversationManagerSingleton:
    """Test singleton pattern for ConversationManager."""
    
    def test_get_conversation_manager_singleton(self):
        """Test get_conversation_manager returns singleton."""
        manager1 = get_conversation_manager()
        manager2 = get_conversation_manager()
        
        assert manager1 is manager2
    
    def test_reset_conversation_manager(self):
        """Test reset_conversation_manager clears singleton."""
        manager1 = get_conversation_manager()
        reset_conversation_manager()
        manager2 = get_conversation_manager()
        
        assert manager1 is not manager2

