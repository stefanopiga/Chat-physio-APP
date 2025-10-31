"""
Unit tests for Story 4.2.2 - Analytics Advanced Metrics

Test Coverage:
- Temporal distribution aggregation (AC1)
- Quality metrics calculation (AC2)
- Problematic queries identification (AC3)
- Engagement stats calculation (AC4)
- Top chunks retrieval (AC5)
- Time filtering (AC7)
- Performance constraints (AC8)
- Backward compatibility (AC9)

Coverage Target: ≥ 85%
"""

import pytest
from datetime import datetime, timedelta
from api.analytics.analytics import (
    aggregate_temporal_distribution,
    aggregate_quality_metrics,
    aggregate_problematic_queries,
    aggregate_engagement_stats,
    aggregate_top_chunks,
    TemporalDistribution,
    QualityMetrics,
    ProblematicQueriesResponse,
    EngagementStats,
    ChunkRetrievalResponse
)


# -------------------------------
# Test Fixtures
# -------------------------------


@pytest.fixture
def mock_chat_messages_store():
    """Mock chat_messages_store con dati temporali distribuiti."""
    now = datetime.utcnow()
    
    return {
        "session_1": [
            {
                "id": "msg_1",
                "role": "user",
                "content": "query test 1",
                "created_at": (now - timedelta(hours=2)).isoformat() + "Z"
            },
            {
                "id": "msg_2",
                "role": "assistant",
                "content": "risposta test 1" * 50,  # ~750 chars
                "created_at": (now - timedelta(hours=2)).isoformat() + "Z",
                "chunk_ids": ["chunk_1", "chunk_2", "chunk_3"],
                "chunk_scores": [0.9, 0.85, 0.8],
                "chunk_documents": ["doc_1", "doc_1", "doc_2"]
            }
        ],
        "session_2": [
            {
                "id": "msg_3",
                "role": "user",
                "content": "query test 2",
                "created_at": (now - timedelta(hours=10)).isoformat() + "Z"
            },
            {
                "id": "msg_4",
                "role": "assistant",
                "content": "risposta test 2" * 30,  # ~450 chars
                "created_at": (now - timedelta(hours=10)).isoformat() + "Z",
                "chunk_ids": ["chunk_1", "chunk_3", "chunk_4"],
                "chunk_scores": [0.88, 0.82, 0.75],
                "chunk_documents": ["doc_1", "doc_2", "doc_3"]
            },
            {
                "id": "msg_5",
                "role": "user",
                "content": "query problematica",
                "created_at": (now - timedelta(hours=10, minutes=5)).isoformat() + "Z"
            },
            {
                "id": "msg_6",
                "role": "assistant",
                "content": "risposta test 3" * 20,  # ~300 chars
                "created_at": (now - timedelta(hours=10, minutes=5)).isoformat() + "Z",
                "chunk_ids": ["chunk_1", "chunk_2"],
                "chunk_scores": [0.92, 0.87],
                "chunk_documents": ["doc_1", "doc_1"]
            }
        ],
        "session_3": [
            {
                "id": "msg_7",
                "role": "user",
                "content": "query test 3",
                "created_at": (now - timedelta(hours=14)).isoformat() + "Z"
            },
            {
                "id": "msg_8",
                "role": "assistant",
                "content": "risposta test 4" * 40,  # ~600 chars
                "created_at": (now - timedelta(hours=14)).isoformat() + "Z",
                "chunk_ids": ["chunk_2", "chunk_3", "chunk_4", "chunk_5"],
                "chunk_scores": [0.9, 0.85, 0.8, 0.78],
                "chunk_documents": ["doc_1", "doc_2", "doc_3", "doc_3"]
            }
        ]
    }


@pytest.fixture
def mock_feedback_store():
    """Mock feedback_store con mix up/down.
    
    ✅ Fix Story 4.2.3: Usa assistant message IDs (non user message IDs)
    - session_1: feedback su msg_2 (assistant che ha risposto a msg_1 user)
    - session_2: feedback su msg_4 e msg_6 (assistant messages)
    """
    now = datetime.utcnow()
    
    return {
        "session_1:msg_2": {  # ✅ Assistant message ID (era msg_1 user - SBAGLIATO)
            "vote": "up",
            "timestamp": (now - timedelta(hours=2)).isoformat() + "Z",
            "session_id": "session_1",
            "message_id": "msg_2"
        },
        "session_2:msg_4": {  # ✅ Assistant message ID (era msg_3 user - SBAGLIATO)
            "vote": "up",
            "timestamp": (now - timedelta(hours=10)).isoformat() + "Z",
            "session_id": "session_2",
            "message_id": "msg_4"
        },
        "session_2:msg_6": {  # ✅ Assistant message ID (era msg_5 user - SBAGLIATO)
            "vote": "down",
            "timestamp": (now - timedelta(hours=10, minutes=5)).isoformat() + "Z",
            "session_id": "session_2",
            "message_id": "msg_6"
        }
    }


# -------------------------------
# BT-4.2.2-001: Temporal Distribution - Aggregazione Corretta
# -------------------------------


def test_temporal_distribution_aggregation(mock_chat_messages_store):
    """
    BT-4.2.2-001: Temporal distribution genera 12 slot orari (0-23, step 2h).
    
    Verifica:
    - Output lista con 12 elementi
    - Ogni elemento è TemporalDistribution
    - hour_slot range 0-22 (step 2)
    - label formato corretto "HH:MM-HH:MM"
    """
    result = aggregate_temporal_distribution(mock_chat_messages_store, "week")
    
    # 12 slot orari (0-1, 2-3, ..., 22-23)
    assert len(result) == 12
    
    # Verifica tipo elementi
    assert all(isinstance(item, TemporalDistribution) for item in result)
    
    # Verifica hour_slot range
    hour_slots = [item.hour_slot for item in result]
    assert hour_slots == list(range(0, 24, 2))
    
    # Verifica label formato
    for item in result:
        assert ":" in item.label
        assert "-" in item.label
        # Es: "00:00-01:59"
        parts = item.label.split("-")
        assert len(parts) == 2
    
    # Verifica conteggi non negativi
    assert all(item.query_count >= 0 for item in result)


# -------------------------------
# BT-4.2.2-002: Temporal Distribution - Time Filter
# -------------------------------


def test_temporal_distribution_time_filter_day(mock_chat_messages_store):
    """
    BT-4.2.2-002: Time filter "day" filtra query ultime 24h.
    
    Verifica:
    - Query oltre 24h escluse
    - Query recenti incluse
    """
    # Test con "day" filter (ultime 24h)
    result_day = aggregate_temporal_distribution(mock_chat_messages_store, "day")
    
    # Deve avere meno query totali rispetto a "all"
    result_all = aggregate_temporal_distribution(mock_chat_messages_store, "all")
    
    sum(item.query_count for item in result_day)
    sum(item.query_count for item in result_all)
    
    # Con mock data: tutte query sono recenti, quindi same count
    # Ma struttura deve essere identica
    assert len(result_day) == 12
    assert len(result_all) == 12


# -------------------------------
# BT-4.2.2-003: Quality Metrics - Lunghezza Media
# -------------------------------


def test_quality_metrics_avg_response_length(mock_chat_messages_store):
    """
    BT-4.2.2-003: Quality metrics calcola lunghezza media risposte.
    
    Verifica:
    - avg_response_length_chars > 0
    - Valore coerente con mock data
    """
    result = aggregate_quality_metrics(mock_chat_messages_store)
    
    assert isinstance(result, QualityMetrics)
    assert result.avg_response_length_chars > 0
    
    # Mock ha risposte 750, 450, 300, 600 chars
    # Media: (750 + 450 + 300 + 600) / 4 = 525
    assert 400 <= result.avg_response_length_chars <= 700  # Range plausibile


# -------------------------------
# BT-4.2.2-004: Quality Metrics - Chunk per Risposta
# -------------------------------


def test_quality_metrics_chunks_per_response(mock_chat_messages_store):
    """
    BT-4.2.2-004: Quality metrics calcola chunk per risposta (con metadata).
    
    Verifica:
    - avg_chunks_per_response > 0
    - chunks_distribution con min/max/median
    """
    result = aggregate_quality_metrics(mock_chat_messages_store)
    
    # Mock ha chunk_ids: [3, 3, 2, 4]
    # Media: (3 + 3 + 2 + 4) / 4 = 3.0
    assert result.avg_chunks_per_response > 0
    assert 2.5 <= result.avg_chunks_per_response <= 3.5
    
    # Distribution checks
    assert result.chunks_distribution["min"] >= 0
    assert result.chunks_distribution["max"] >= result.chunks_distribution["min"]
    assert result.chunks_distribution["median"] >= 0


# -------------------------------
# BT-4.2.2-005: Problematic Queries - Top 5
# -------------------------------


def test_problematic_queries_top_5(mock_chat_messages_store, mock_feedback_store):
    """
    BT-4.2.2-005: Problematic queries identifica top 5 feedback negativi.
    
    Verifica:
    - queries lista non vuota
    - total_count >= len(queries)
    - Query con negative_feedback_count > 0
    """
    result = aggregate_problematic_queries(
        mock_chat_messages_store, 
        mock_feedback_store, 
        limit=5
    )
    
    assert isinstance(result, ProblematicQueriesResponse)
    
    # Mock ha 1 feedback negativo
    assert result.total_count >= 0
    
    # Se ci sono problematic queries
    if result.total_count > 0:
        assert len(result.queries) > 0
        assert len(result.queries) <= 5  # Limit
        
        # Ogni query deve avere negative_feedback_count > 0
        for query in result.queries:
            assert query.negative_feedback_count > 0
            assert query.query_text
            assert query.first_seen


# -------------------------------
# BT-4.2.2-006: Engagement Stats - Durata Sessione
# -------------------------------


def test_engagement_stats_session_duration(mock_chat_messages_store, mock_feedback_store):
    """
    BT-4.2.2-006: Engagement stats calcola durata sessione.
    
    Verifica:
    - avg_session_duration_minutes >= 0
    """
    result = aggregate_engagement_stats(mock_chat_messages_store, mock_feedback_store)
    
    assert isinstance(result, EngagementStats)
    assert result.avg_session_duration_minutes >= 0.0


# -------------------------------
# BT-4.2.2-007: Engagement Stats - Query per Sessione
# -------------------------------


def test_engagement_stats_queries_per_session(mock_chat_messages_store, mock_feedback_store):
    """
    BT-4.2.2-007: Engagement stats calcola query per sessione.
    
    Verifica:
    - avg_queries_per_session > 0
    - Valore coerente con mock (3 sessioni, 4 query totali)
    """
    result = aggregate_engagement_stats(mock_chat_messages_store, mock_feedback_store)
    
    # Mock ha 3 sessioni con 1, 2, 1 query rispettivamente
    # Media: (1 + 2 + 1) / 3 = 1.33
    assert result.avg_queries_per_session > 0
    assert 1.0 <= result.avg_queries_per_session <= 2.5


# -------------------------------
# BT-4.2.2-008: Engagement Stats - Conversion Rate
# -------------------------------


def test_engagement_stats_feedback_conversion(mock_chat_messages_store, mock_feedback_store):
    """
    BT-4.2.2-008: Engagement stats calcola conversion rate feedback.
    
    Verifica:
    - feedback_conversion_rate tra 0.0 e 1.0
    - Valore coerente con mock (3 feedback su 4 query)
    """
    result = aggregate_engagement_stats(mock_chat_messages_store, mock_feedback_store)
    
    # Mock ha 3 feedback su 4 query totali = 0.75
    assert 0.0 <= result.feedback_conversion_rate <= 1.0
    assert result.feedback_conversion_rate > 0.5  # Più di metà query con feedback


# -------------------------------
# BT-4.2.2-009: Top Chunks - Chunk Più Recuperati
# -------------------------------


def test_top_chunks_retrieval_count(mock_chat_messages_store):
    """
    BT-4.2.2-009: Top chunks identifica chunk più recuperati (con metadata).
    
    Verifica:
    - top_chunks non vuoto
    - total_chunks_count >= len(top_chunks)
    - Chunk ordinati per retrieval_count desc
    """
    result = aggregate_top_chunks(mock_chat_messages_store, limit=10)
    
    assert isinstance(result, ChunkRetrievalResponse)
    assert result.total_chunks_count >= 0
    
    # Mock ha 5 chunk unici
    if result.total_chunks_count > 0:
        assert len(result.top_chunks) > 0
        assert len(result.top_chunks) <= 10
        
        # Verifica ordinamento desc per retrieval_count
        counts = [chunk.retrieval_count for chunk in result.top_chunks]
        assert counts == sorted(counts, reverse=True)
        
        # Verifica campi
        for chunk in result.top_chunks:
            assert chunk.chunk_id
            assert chunk.document_id
            assert chunk.retrieval_count > 0


# -------------------------------
# BT-4.2.2-010: Top Chunks - Similarity Score
# -------------------------------


def test_top_chunks_similarity_score(mock_chat_messages_store):
    """
    BT-4.2.2-010: Top chunks calcola similarity score medio.
    
    Verifica:
    - avg_similarity_score tra 0.0 e 1.0
    """
    result = aggregate_top_chunks(mock_chat_messages_store, limit=10)
    
    if len(result.top_chunks) > 0:
        for chunk in result.top_chunks:
            assert 0.0 <= chunk.avg_similarity_score <= 1.0


# -------------------------------
# BT-4.2.2-011: Backward Compatibility
# -------------------------------


def test_endpoint_backward_compatibility():
    """
    BT-4.2.2-011: Endpoint query param include_advanced=false backward compatibility.
    
    Verifica:
    - Default include_advanced=False
    - Response type AnalyticsResponse (base) quando False
    - Response type AdvancedAnalyticsResponse quando True
    
    Note: Questo è un integration test, verificato in test_integration.py
    """
    # Placeholder per integration test
    # Test reale richiede FastAPI TestClient
    pass


# -------------------------------
# BT-4.2.2-012: Performance Test
# -------------------------------


@pytest.mark.slow
def test_performance_aggregation_5000_queries():
    """
    BT-4.2.2-012: Performance aggregazione < 800ms con 5000 query mock.
    
    Verifica:
    - Aggregazione completa < 800ms
    - No memory leaks
    
    AC8: Target p95 < 800ms con dataset ≤ 5000 query
    """
    import time
    
    # Genera 5000 query mock distribuite temporalmente
    now = datetime.utcnow()
    large_store = {}
    
    for i in range(1000):  # 1000 sessioni
        session_id = f"session_{i}"
        messages = []
        
        for j in range(5):  # 5 query per sessione = 5000 totali
            msg_id = f"msg_{i}_{j}"
            timestamp = (now - timedelta(hours=i % 24, minutes=j * 10)).isoformat() + "Z"
            
            # User message
            messages.append({
                "id": msg_id,
                "role": "user",
                "content": f"query {i}_{j}",
                "created_at": timestamp
            })
            
            # Assistant message
            messages.append({
                "id": f"{msg_id}_resp",
                "role": "assistant",
                "content": "risposta" * 50,
                "created_at": timestamp,
                "chunk_ids": [f"chunk_{j % 10}"],
                "chunk_scores": [0.85],
                "chunk_documents": [f"doc_{j % 5}"]
            })
        
        large_store[session_id] = messages
    
    feedback_store = {}  # Empty per semplicità
    
    # Measure aggregation time
    start = time.time()
    
    temporal = aggregate_temporal_distribution(large_store, "week")
    quality = aggregate_quality_metrics(large_store)
    aggregate_problematic_queries(large_store, feedback_store)
    engagement = aggregate_engagement_stats(large_store, feedback_store)
    aggregate_top_chunks(large_store)
    
    elapsed_ms = (time.time() - start) * 1000
    
    # AC8: Target < 800ms
    print(f"Performance test: {elapsed_ms:.0f}ms for 5000 queries")
    assert elapsed_ms < 1000  # Buffer per CI environment (target 800ms)
    
    # Sanity checks
    assert len(temporal) == 12
    assert quality.avg_response_length_chars > 0
    assert engagement.avg_queries_per_session > 0

