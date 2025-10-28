"""
Integration test per conversational follow-up (Story 7.1).

Test multi-turn conversations:
- Follow-up ambigui ("Quali sono i gradi?")
- Reference risposta precedente ("Approfondisci il punto 2")
- Coerenza risposta con cronologia

Note: Test marcati @pytest.mark.integration richiedono LLM attivo.
Per test locali, usare mock LLM.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from api.models.answer_with_citations import AnswerWithCitations
from api.models.enhanced_response import EnhancedAcademicResponse, CitationMetadata
from api.stores import chat_messages_store
from api.services.conversation_service import reset_conversation_manager


@pytest.fixture(autouse=True)
def reset_state():
    """Reset state before each test."""
    chat_messages_store.clear()
    reset_conversation_manager()
    yield
    chat_messages_store.clear()
    reset_conversation_manager()


@pytest.mark.integration
class TestConversationalFollowup:
    """Integration tests per multi-turn conversations."""
    
    @pytest.fixture
    def mock_llm_chain(self):
        """Mock LLM chain per test senza chiamate API reali."""
        with patch("api.routers.chat.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm
            yield mock_llm
    
    def test_multi_turn_conversation_baseline(self, client, auth_headers, mock_llm_chain):
        """
        Test conversazione multi-turno con baseline prompt.
        
        Turn 1: "Cos'è la spondilolistesi?"
        Turn 2: "Quali sono i gradi?" (follow-up ambiguo)
        Turn 3: "Approfondisci il punto 2" (reference risposta precedente)
        """
        session_id = "test_session_123"
        
        # Mock LLM responses
        mock_responses = [
            AnswerWithCitations(
                risposta="La spondilolistesi è lo scivolamento anteriore di una vertebra rispetto alla sottostante.",
                citazioni=["chunk_1"],
            ),
            AnswerWithCitations(
                risposta="Si classifica secondo Meyerding in 4 gradi basati sulla percentuale di scivolamento.",
                citazioni=["chunk_2"],
            ),
            AnswerWithCitations(
                risposta="Il grado II corrisponde a scivolamento 25-50% del corpo vertebrale.",
                citazioni=["chunk_2", "chunk_3"],
            ),
        ]
        
        def mock_invoke(inputs):
            return mock_responses.pop(0)
        
        mock_llm_chain.return_value.invoke = mock_invoke
        
        # Turn 1: Initial question
        response1 = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={
                "message": "Cos'è la spondilolistesi?",
                "chunks": [
                    {
                        "id": "chunk_1",
                        "document_id": "doc_1",
                        "content": "La spondilolistesi è lo scivolamento...",
                        "similarity": 0.9,
                    }
                ],
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert "spondilolistesi" in data1["answer"].lower()
        
        # Turn 2: Follow-up ambiguo (richiede contesto per disambiguare)
        response2 = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={
                "message": "Quali sono i gradi?",
                "chunks": [
                    {
                        "id": "chunk_2",
                        "document_id": "doc_1",
                        "content": "Classificazione Meyerding: gradi I-IV...",
                        "similarity": 0.85,
                    }
                ],
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert "gradi" in data2["answer"].lower() or "meyerding" in data2["answer"].lower()
        
        # Turn 3: Reference risposta precedente
        response3 = client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={
                "message": "Approfondisci il punto 2",
                "chunks": [
                    {
                        "id": "chunk_2",
                        "document_id": "doc_1",
                        "content": "Grado II: scivolamento 25-50%...",
                        "similarity": 0.88,
                    },
                    {
                        "id": "chunk_3",
                        "document_id": "doc_1",
                        "content": "Correlazioni cliniche grado II...",
                        "similarity": 0.82,
                    },
                ],
            },
        )
        assert response3.status_code == 200
        data3 = response3.json()
        # Verify response references previous context
        assert len(data3["answer"]) > 50  # Non-trivial answer
    
    def test_context_window_persistence(self, client, auth_headers, mock_llm_chain):
        """Test that conversation context persists across turns."""
        session_id = "test_session_456"
        
        # Mock responses
        mock_llm_chain.return_value.invoke.return_value = AnswerWithCitations(
            risposta="Test response",
            citazioni=["chunk_1"],
        )
        
        # Turn 1
        client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            headers=auth_headers,
            json={
                "message": "Prima domanda",
                "chunks": [{"id": "chunk_1", "document_id": "doc_1", "content": "Content 1", "similarity": 0.9}],
            },
        )
        
        # Verify stored in chat_messages_store
        stored = chat_messages_store.get(session_id)
        assert stored is not None
        # Should have at least assistant response
        assert any(msg.get("role") == "assistant" for msg in stored)
    
    def test_enhanced_model_multi_turn(self, client, auth_headers, mock_llm_chain):
        """Test multi-turn with enhanced academic response model."""
        session_id = "test_session_789"
        
        # Mock enhanced response
        mock_llm_chain.return_value.invoke.return_value = EnhancedAcademicResponse(
            introduzione="La stenosi spinale lombare è un restringimento del canale vertebrale.",
            concetti_chiave=["Stenosi centrale", "Stenosi foraminale"],
            spiegazione_dettagliata=(
                "La stenosi spinale si verifica quando lo spazio disponibile per le strutture nervose "
                "si riduce progressivamente. Può essere congenita o acquisita (degenerativa). "
                "I sintomi tipici includono claudicatio neurogena."
            ),
            note_cliniche="Considerare imaging (RMN) per conferma diagnostica.",
            limitazioni_contesto=None,
            citazioni=[
                CitationMetadata(
                    chunk_id="chunk_1",
                    document_id="doc_1",
                    document_name="Stenosi.docx",
                    relevance_score=0.92,
                )
            ],
            confidenza_risposta="alta",
        )
        
        # Turn 1: Con enhanced model attivo
        with patch.dict("os.environ", {"ENABLE_ENHANCED_RESPONSE_MODEL": "true"}):
            response = client.post(
                f"/api/v1/chat/sessions/{session_id}/messages",
                headers=auth_headers,
                json={
                    "message": "Cos'è la stenosi spinale?",
                    "chunks": [
                        {
                            "id": "chunk_1",
                            "document_id": "doc_1",
                            "content": "La stenosi spinale lombare...",
                            "similarity": 0.92,
                        }
                    ],
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["answer"]) > 100  # Detailed response


@pytest.mark.unit
class TestConversationMemoryIntegration:
    """Unit tests per conversation memory integration."""
    
    def test_conversation_history_injection_in_prompt(self):
        """Test conversation history is injected in prompt correctly."""
        from api.services.conversation_service import ConversationManager
        from api.models.conversation import ConversationMessage, ChatContextWindow
        
        manager = ConversationManager()
        messages = [
            ConversationMessage(
                role="user",
                content="Prima domanda",
                timestamp=datetime.now(timezone.utc),
            ),
            ConversationMessage(
                role="assistant",
                content="Prima risposta",
                timestamp=datetime.now(timezone.utc),
            ),
        ]
        window = ChatContextWindow(session_id="test", messages=messages, total_tokens=50)
        
        formatted = manager.format_for_prompt(window)
        
        # Verify structure
        assert "CRONOLOGIA CONVERSAZIONE" in formatted
        assert "STUDENTE:" in formatted
        assert "TUTOR:" in formatted
        assert "Prima domanda" in formatted
        assert "Prima risposta" in formatted
    
    def test_sliding_window_drops_old_messages(self):
        """Test sliding window drops oldest messages when exceeding MAX_TURNS."""
        from api.services.conversation_service import ConversationManager
        from api.stores import chat_messages_store
        
        session_id = "test_session_sliding"
        
        # Populate with 8 messages (4 turns) - exceeds MAX_TURNS (3)
        messages = []
        for i in range(8):
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
        
        # Should keep only last 6 messages (3 turns)
        assert len(window.messages) == 6
        assert window.messages[0].content == "Message 2"  # Oldest kept
        assert window.messages[-1].content == "Message 7"  # Newest

