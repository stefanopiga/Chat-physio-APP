"""
Test suite per Story 4.2.3: Bug Fix - Feedback Aggregation

Verifica che il fix per il pairing corretto message_id funzioni:
- AC4: Unit tests per validare il fix
- TECH-002: Edge cases di pairing (messaggi di sistema, sequenze)

Test Coverage:
- Pairing corretto user → assistant message ID
- Query problematiche identificate con feedback negativo reale
- Tasso conversione feedback calcolato correttamente
- Edge cases: system messages, sessioni incomplete, feedback mancanti
"""

from datetime import datetime, timezone
from api.analytics.analytics import (
    aggregate_problematic_queries,
    aggregate_engagement_stats,
    get_assistant_id_for_user_message
)


class TestHelperMessagePairing:
    """Test per utility helper get_assistant_id_for_user_message()"""
    
    def test_simple_pairing_user_assistant(self):
        """Caso base: user → assistant"""
        messages = [
            {"role": "user", "id": "frontend-uuid-1", "content": "Query 1"},
            {"role": "assistant", "id": "backend-msg-1", "content": "Response 1"}
        ]
        
        assistant_id = get_assistant_id_for_user_message(messages, 0)
        assert assistant_id == "backend-msg-1"
    
    def test_pairing_with_system_message_between(self):
        """Edge case: user → system → assistant (TECH-002)"""
        messages = [
            {"role": "user", "id": "frontend-uuid-1", "content": "Query 1"},
            {"role": "system", "content": "System message"},
            {"role": "assistant", "id": "backend-msg-1", "content": "Response 1"}
        ]
        
        # Helper dovrebbe saltare system message e trovare assistant
        assistant_id = get_assistant_id_for_user_message(messages, 0)
        assert assistant_id == "backend-msg-1"
    
    def test_pairing_multiple_conversations(self):
        """Test con conversazione multipla: trova assistant corretto per ogni user"""
        messages = [
            {"role": "user", "id": "frontend-uuid-1", "content": "Query 1"},
            {"role": "assistant", "id": "backend-msg-1", "content": "Response 1"},
            {"role": "user", "id": "frontend-uuid-2", "content": "Query 2"},
            {"role": "assistant", "id": "backend-msg-2", "content": "Response 2"},
            {"role": "user", "id": "frontend-uuid-3", "content": "Query 3"},
            {"role": "assistant", "id": "backend-msg-3", "content": "Response 3"}
        ]
        
        assert get_assistant_id_for_user_message(messages, 0) == "backend-msg-1"
        assert get_assistant_id_for_user_message(messages, 2) == "backend-msg-2"
        assert get_assistant_id_for_user_message(messages, 4) == "backend-msg-3"
    
    def test_pairing_no_assistant_found(self):
        """Edge case: user message senza risposta assistant (TECH-002)"""
        messages = [
            {"role": "user", "id": "frontend-uuid-1", "content": "Query senza risposta"}
        ]
        
        assistant_id = get_assistant_id_for_user_message(messages, 0)
        assert assistant_id is None
    
    def test_pairing_last_user_message(self):
        """Edge case: ultimo user message senza assistant (conversazione in corso)"""
        messages = [
            {"role": "user", "id": "frontend-uuid-1", "content": "Query 1"},
            {"role": "assistant", "id": "backend-msg-1", "content": "Response 1"},
            {"role": "user", "id": "frontend-uuid-2", "content": "Query 2 senza risposta"}
        ]
        
        assistant_id = get_assistant_id_for_user_message(messages, 2)
        assert assistant_id is None


class TestProblematicQueriesWithRealFeedback:
    """Test AC4: Verifica che query con feedback negativo vengano trovate"""
    
    def test_single_query_with_negative_feedback(self):
        """Query singola con feedback negativo → deve essere identificata"""
        session_id = "test-session-1"
        backend_msg_id = "backend-msg-123"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "id": "frontend-uuid-1", "content": "Lombosciatalgia trattamento"},
                {"role": "assistant", "id": backend_msg_id, "content": "Risposta..."}
            ]
        }
        
        feedback_store = {
            f"{session_id}:{backend_msg_id}": {
                "vote": "down",
                "created_at": datetime.now(timezone.utc).isoformat(),  # ✅ Backend usa "created_at"
                "session_id": session_id,
                "message_id": backend_msg_id
            }
        }
        
        result = aggregate_problematic_queries(chat_messages_store, feedback_store)
        
        # AC4: Query problematica identificata correttamente
        assert result.total_count == 1
        assert len(result.queries) == 1
        assert result.queries[0].query_text == "lombosciatalgia trattamento"
        assert result.queries[0].negative_feedback_count == 1
    
    def test_multiple_queries_different_feedback(self):
        """3 query: 2 negative, 1 positive → solo 2 problematiche"""
        session_id = "test-session-2"
        backend_msg_1 = "backend-msg-1"
        backend_msg_2 = "backend-msg-2"
        backend_msg_3 = "backend-msg-3"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query con thumbs down 1"},
                {"role": "assistant", "id": backend_msg_1},
                {"role": "user", "content": "Query con thumbs up"},
                {"role": "assistant", "id": backend_msg_2},
                {"role": "user", "content": "Query con thumbs down 2"},
                {"role": "assistant", "id": backend_msg_3}
            ]
        }
        
        feedback_store = {
            f"{session_id}:{backend_msg_1}": {"vote": "down"},
            f"{session_id}:{backend_msg_2}": {"vote": "up"},
            f"{session_id}:{backend_msg_3}": {"vote": "down"}
        }
        
        result = aggregate_problematic_queries(chat_messages_store, feedback_store)
        
        assert result.total_count == 2  # Solo query con thumbs down
        assert len(result.queries) == 2
        query_texts = {q.query_text for q in result.queries}
        assert "query con thumbs down 1" in query_texts
        assert "query con thumbs down 2" in query_texts
    
    def test_repeated_query_with_multiple_negative_feedback(self):
        """Stessa query ripetuta con feedback negativo → count aggregato"""
        session_1 = "session-1"
        session_2 = "session-2"
        msg_1 = "msg-1"
        msg_2 = "msg-2"
        
        chat_messages_store = {
            session_1: [
                {"role": "user", "content": "Ernia discale sintomi"},
                {"role": "assistant", "id": msg_1}
            ],
            session_2: [
                {"role": "user", "content": "Ernia discale sintomi"},  # Stessa query
                {"role": "assistant", "id": msg_2}
            ]
        }
        
        feedback_store = {
            f"{session_1}:{msg_1}": {"vote": "down"},
            f"{session_2}:{msg_2}": {"vote": "down"}
        }
        
        result = aggregate_problematic_queries(chat_messages_store, feedback_store)
        
        # Stessa query → count = 2
        assert result.total_count == 1  # 1 query unica
        assert result.queries[0].query_text == "ernia discale sintomi"
        assert result.queries[0].negative_feedback_count == 2  # 2 feedback negativi
    
    def test_empty_feedback_store(self):
        """Nessun feedback → lista vuota"""
        chat_messages_store = {
            "session-1": [
                {"role": "user", "content": "Query senza feedback"},
                {"role": "assistant", "id": "msg-1"}
            ]
        }
        feedback_store = {}
        
        result = aggregate_problematic_queries(chat_messages_store, feedback_store)
        
        assert result.total_count == 0
        assert len(result.queries) == 0
    
    def test_user_message_without_assistant_response(self):
        """Edge case TECH-002: User message senza risposta assistant → ignorato"""
        session_id = "session-incomplete"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "id": "frontend-uuid-1", "content": "Query senza risposta"}
                # Nessun assistant message corrispondente
            ]
        }
        
        feedback_store = {}
        
        result = aggregate_problematic_queries(chat_messages_store, feedback_store)
        
        # Nessun crash, query ignorata correttamente
        assert result.total_count == 0
        assert len(result.queries) == 0


class TestEngagementFeedbackConversion:
    """Test AC4: Verifica calcolo corretto tasso conversione feedback"""
    
    def test_feedback_conversion_100_percent(self):
        """3 query, 3 con feedback → 100% conversione"""
        session_id = "session-full-feedback"
        msg_1 = "backend-msg-1"
        msg_2 = "backend-msg-2"
        msg_3 = "backend-msg-3"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query 1"},
                {"role": "assistant", "id": msg_1},
                {"role": "user", "content": "Query 2"},
                {"role": "assistant", "id": msg_2},
                {"role": "user", "content": "Query 3"},
                {"role": "assistant", "id": msg_3}
            ]
        }
        
        feedback_store = {
            f"{session_id}:{msg_1}": {"vote": "up"},
            f"{session_id}:{msg_2}": {"vote": "down"},
            f"{session_id}:{msg_3}": {"vote": "up"}
        }
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # AC4: 3 query con feedback / 3 totali = 100%
        assert result.feedback_conversion_rate == 1.0  # 100%
        assert result.avg_queries_per_session == 3.0
    
    def test_feedback_conversion_66_percent(self):
        """3 query, 2 con feedback → 66.7% conversione (AC4 example)"""
        session_id = "session-partial-feedback"
        msg_1 = "backend-msg-1"
        msg_2 = "backend-msg-2"
        msg_3 = "backend-msg-3"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query 1"},
                {"role": "assistant", "id": msg_1},
                {"role": "user", "content": "Query 2"},
                {"role": "assistant", "id": msg_2},
                {"role": "user", "content": "Query 3 senza feedback"},
                {"role": "assistant", "id": msg_3}
            ]
        }
        
        feedback_store = {
            f"{session_id}:{msg_1}": {"vote": "up"},
            f"{session_id}:{msg_2}": {"vote": "down"}
            # msg_3 senza feedback
        }
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # AC4: 2 query con feedback / 3 totali = 66.7%
        assert result.feedback_conversion_rate > 0.66
        assert result.feedback_conversion_rate < 0.67
    
    def test_feedback_conversion_40_percent(self):
        """5 query, 2 con feedback → 40% conversione (AC3 example)"""
        session_id = "session-low-feedback"
        msg_1 = "backend-msg-1"
        msg_2 = "backend-msg-2"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query 1"},
                {"role": "assistant", "id": msg_1},
                {"role": "user", "content": "Query 2"},
                {"role": "assistant", "id": msg_2},
                {"role": "user", "content": "Query 3"},
                {"role": "assistant", "id": "msg-3"},
                {"role": "user", "content": "Query 4"},
                {"role": "assistant", "id": "msg-4"},
                {"role": "user", "content": "Query 5"},
                {"role": "assistant", "id": "msg-5"}
            ]
        }
        
        feedback_store = {
            f"{session_id}:{msg_1}": {"vote": "up"},
            f"{session_id}:{msg_2}": {"vote": "down"}
        }
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # AC3: 2 query con feedback / 5 totali = 40%
        assert result.feedback_conversion_rate == 0.4  # Esatto 40%
    
    def test_feedback_conversion_zero_percent(self):
        """3 query, 0 con feedback → 0% conversione"""
        session_id = "session-no-feedback"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query 1"},
                {"role": "assistant", "id": "msg-1"},
                {"role": "user", "content": "Query 2"},
                {"role": "assistant", "id": "msg-2"}
            ]
        }
        
        feedback_store = {}
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        assert result.feedback_conversion_rate == 0.0
        assert result.avg_queries_per_session == 2.0
    
    def test_feedback_conversion_multiple_sessions(self):
        """2 sessioni: session1 (2/2 feedback), session2 (1/3 feedback) → Media aggregata"""
        session_1 = "session-1"
        session_2 = "session-2"
        
        chat_messages_store = {
            session_1: [
                {"role": "user", "content": "S1 Query 1"},
                {"role": "assistant", "id": "s1-msg-1"},
                {"role": "user", "content": "S1 Query 2"},
                {"role": "assistant", "id": "s1-msg-2"}
            ],
            session_2: [
                {"role": "user", "content": "S2 Query 1"},
                {"role": "assistant", "id": "s2-msg-1"},
                {"role": "user", "content": "S2 Query 2"},
                {"role": "assistant", "id": "s2-msg-2"},
                {"role": "user", "content": "S2 Query 3"},
                {"role": "assistant", "id": "s2-msg-3"}
            ]
        }
        
        feedback_store = {
            # Session 1: 2 feedback / 2 query = 100%
            f"{session_1}:s1-msg-1": {"vote": "up"},
            f"{session_1}:s1-msg-2": {"vote": "up"},
            # Session 2: 1 feedback / 3 query = 33.3%
            f"{session_2}:s2-msg-2": {"vote": "down"}
        }
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # Totale: 3 query con feedback / 5 query totali = 60%
        assert result.feedback_conversion_rate == 0.6
    
    def test_edge_case_user_message_without_assistant(self):
        """Edge case TECH-002: User message finale senza assistant → contato come query ma no feedback possibile"""
        session_id = "session-incomplete"
        msg_1 = "backend-msg-1"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Query 1"},
                {"role": "assistant", "id": msg_1},
                {"role": "user", "content": "Query 2 senza risposta"}
                # Conversazione in corso, no assistant per Query 2
            ]
        }
        
        feedback_store = {
            f"{session_id}:{msg_1}": {"vote": "up"}
        }
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # 1 query con feedback / 2 query totali = 50%
        assert result.feedback_conversion_rate == 0.5
        assert result.avg_queries_per_session == 2.0


class TestPerformanceOptimization:
    """Test che l'ottimizzazione O(1) lookup funzioni (PERF-001)"""
    
    def test_large_feedback_store_performance(self):
        """Simula feedback store grande → verifica no performance degradation"""
        # Setup: 1 sessione con 3 query, feedback store con 100+ entries da altre sessioni
        target_session = "target-session"
        msg_1 = "target-msg-1"
        
        chat_messages_store = {
            target_session: [
                {"role": "user", "content": "Query reale"},
                {"role": "assistant", "id": msg_1}
            ]
        }
        
        # Popola feedback store con 100 entries di altre sessioni (noise)
        feedback_store = {
            f"other-session-{i}:msg-{i}": {"vote": "up"}
            for i in range(100)
        }
        # Aggiungi feedback per la sessione target
        feedback_store[f"{target_session}:{msg_1}"] = {"vote": "down"}
        
        result = aggregate_engagement_stats(chat_messages_store, feedback_store)
        
        # Deve trovare il feedback corretto nonostante 100+ entries
        # Performance: O(1) lookup con set pre-costruito (no substring scan)
        assert result.feedback_conversion_rate == 1.0  # 1 query con feedback / 1 totale


class TestRegressionExistingFunctionality:
    """Test AC6: Verifica che aggregate_analytics() continui a funzionare"""
    
    def test_aggregate_analytics_unchanged(self):
        """aggregate_analytics() non modificato → deve funzionare come prima"""
        from api.analytics.analytics import aggregate_analytics
        
        session_id = "test-session"
        
        chat_messages_store = {
            session_id: [
                {"role": "user", "content": "Test query"},
                {"role": "assistant", "id": "msg-1"}
            ]
        }
        
        feedback_store = {
            f"{session_id}:msg-1": {"vote": "up"}
        }
        
        # Parametro latency samples (vuoto per questo test)
        ag_latency_samples_ms = [100, 150, 200]
        
        # Funzione non modificata → deve funzionare
        result = aggregate_analytics(chat_messages_store, feedback_store, ag_latency_samples_ms)
        
        # Feedback summary deve funzionare (itera su values)
        assert result.feedback_summary.thumbs_up == 1
        assert result.feedback_summary.thumbs_down == 0

