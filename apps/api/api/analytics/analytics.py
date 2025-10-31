"""
Analytics Endpoint - Story 4.2 & 4.2.2
Endpoint: GET /api/v1/admin/analytics

Aggregazione dati da store in-memory per dashboard analytics.
Dati volatili (tech debt R-4.2-1 accepted).

Story 4.2.2: Extended with advanced analytics metrics
"""

import hashlib
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pydantic import BaseModel
from fastapi import APIRouter

log = logging.getLogger(__name__)


router = APIRouter()


# -------------------------------
# Response Models - Story 4.2 (Base)
# -------------------------------


class OverviewStats(BaseModel):
    total_queries: int
    total_sessions: int
    feedback_ratio: float  # up/(up+down), 0.0-1.0
    avg_latency_ms: int


class QueryStat(BaseModel):
    query_text: str
    count: int
    last_queried_at: str  # ISO datetime


class FeedbackSummary(BaseModel):
    thumbs_up: int
    thumbs_down: int
    ratio: float  # up/(up+down)


class PerformanceMetrics(BaseModel):
    latency_p95_ms: int
    latency_p99_ms: int
    sample_count: int


class AnalyticsResponse(BaseModel):
    overview: OverviewStats
    top_queries: list[QueryStat]
    feedback_summary: FeedbackSummary
    performance_metrics: PerformanceMetrics


# -------------------------------
# Response Models - Story 4.2.2 (Advanced)
# -------------------------------


class TemporalDistribution(BaseModel):
    hour_slot: int  # 0-23
    query_count: int
    label: str  # "00:00-01:59" - BACKEND GENERATED (i18n source: backend logic)


class QualityMetrics(BaseModel):
    avg_response_length_chars: int
    avg_chunks_per_response: float
    chunks_distribution: dict[str, int]  # {"min": 2, "max": 10, "median": 5}


class ProblematicQuery(BaseModel):
    query_text: str
    negative_feedback_count: int
    first_seen: str  # ISO datetime


class ProblematicQueriesResponse(BaseModel):
    queries: list[ProblematicQuery]
    total_count: int  # AC3: Total count of problematic queries (not just top 5)


class EngagementStats(BaseModel):
    avg_session_duration_minutes: float
    avg_queries_per_session: float
    feedback_conversion_rate: float  # % query con feedback


class ChunkRetrievalStat(BaseModel):
    chunk_id: str
    document_id: str
    retrieval_count: int
    avg_similarity_score: float


class ChunkRetrievalResponse(BaseModel):
    top_chunks: list[ChunkRetrievalStat]
    total_chunks_count: int  # AC5: Total count of unique chunks used


class AdvancedAnalyticsResponse(BaseModel):
    # Story 4.2 metriche base (backward compatibility)
    overview: OverviewStats
    top_queries: list[QueryStat]
    feedback_summary: FeedbackSummary
    performance_metrics: PerformanceMetrics
    
    # NEW: Story 4.2.2 metriche avanzate
    temporal_distribution: list[TemporalDistribution]
    quality_metrics: QualityMetrics
    problematic_queries: ProblematicQueriesResponse  # AC3: includes total_count
    engagement_stats: EngagementStats
    top_chunks: ChunkRetrievalResponse  # AC5: includes total_chunks_count


# -------------------------------
# Utility Functions
# -------------------------------


def _hash_session_id(session_id: str) -> str:
    """Hash SHA256 session_id per privacy (R-4.2-2)."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def _percentile(values: list[float], p: float) -> float:
    """Calcola percentile (nearest-rank)."""
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = round((p / 100.0) * (len(ordered) - 1))
    idx = max(0, min(len(ordered) - 1, int(idx)))
    return float(ordered[idx])


def _get_time_cutoff(filter_option: str) -> datetime | None:
    """
    Helper per calcolo cutoff temporale.
    
    AC7: Mappatura filtri UI→API:
        "day" → ultime 24h
        "week" → ultime 7 giorni (default)
        "month" → ultimi 30 giorni
        "all" → nessun filtro
    
    Timezone: UTC (AC7)
    Finestre temporali: Inclusive (es: day = da now - 24h a now)
    
    Performance Constraint (AC8):
        Max window: 30 giorni (in-memory limitation until Story 4.2.1)
        "month" e "all" limitati a 30 giorni retroattivi
    """
    now = datetime.utcnow()  # AC7: UTC timezone
    if filter_option == "day":
        return now - timedelta(days=1)
    elif filter_option == "week":
        return now - timedelta(weeks=1)
    elif filter_option == "month":
        return now - timedelta(days=30)  # AC8: Max 30 giorni (tech debt constraint)
    else:  # "all"
        return now - timedelta(days=30)  # AC8: Capped at 30 days until Story 4.2.1


# -------------------------------
# Aggregation Functions - Story 4.2 (Base)
# -------------------------------


def aggregate_analytics(
    chat_messages_store: dict,
    feedback_store: dict,
    ag_latency_samples_ms: list[int],
) -> AnalyticsResponse:
    """
    Aggrega dati analytics da store in-memory.
    
    Args:
        chat_messages_store: dict[session_id, list[message]]
        feedback_store: dict[key, feedback_record]
        ag_latency_samples_ms: list[int]
        
    Returns:
        AnalyticsResponse con statistiche aggregate
    """
    
    # Overview: conteggio query e sessioni
    total_sessions = len(chat_messages_store)
    total_queries = 0
    query_texts: list[str] = []
    query_timestamps: dict[str, str] = {}
    
    for session_id, messages in chat_messages_store.items():
        for msg in messages:
            if msg.get("role") == "user":
                total_queries += 1
                content = (msg.get("content") or "").strip().lower()
                if content:
                    query_texts.append(content)
                    query_timestamps[content] = msg.get("created_at", "")
            # Assistant messages for query tracking
            elif msg.get("role") == "assistant":
                # Conteggio query inferito da assistant responses
                pass
    
    # Top queries con normalizzazione case-insensitive
    query_counts = Counter(query_texts)
    top_queries = [
        QueryStat(
            query_text=q,
            count=c,
            last_queried_at=query_timestamps.get(q, "")
        )
        for q, c in query_counts.most_common(10)
    ]
    
    # Feedback ratio
    feedback_votes = [f.get("vote") for f in feedback_store.values()]
    thumbs_up = feedback_votes.count("up")
    thumbs_down = feedback_votes.count("down")
    feedback_ratio = thumbs_up / (thumbs_up + thumbs_down) if (thumbs_up + thumbs_down) > 0 else 0.0
    
    feedback_summary = FeedbackSummary(
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        ratio=feedback_ratio
    )
    
    # Performance metrics
    sample_count = len(ag_latency_samples_ms)
    latency_p95_ms = int(_percentile(ag_latency_samples_ms, 95.0)) if sample_count > 0 else 0
    latency_p99_ms = int(_percentile(ag_latency_samples_ms, 99.0)) if sample_count > 0 else 0
    
    performance_metrics = PerformanceMetrics(
        latency_p95_ms=latency_p95_ms,
        latency_p99_ms=latency_p99_ms,
        sample_count=sample_count
    )
    
    # Avg latency
    avg_latency_ms = int(sum(ag_latency_samples_ms) / sample_count) if sample_count > 0 else 0
    
    overview = OverviewStats(
        total_queries=total_queries,
        total_sessions=total_sessions,
        feedback_ratio=feedback_ratio,
        avg_latency_ms=avg_latency_ms
    )
    
    return AnalyticsResponse(
        overview=overview,
        top_queries=top_queries,
        feedback_summary=feedback_summary,
        performance_metrics=performance_metrics
    )


# -------------------------------
# Aggregation Functions - Story 4.2.2 (Advanced)
# -------------------------------


def aggregate_temporal_distribution(
    chat_messages_store: dict,
    time_filter: str = "week"  # "day", "week", "month", "all"
) -> list[TemporalDistribution]:
    """
    Aggrega query per fascia oraria (slot 2h).
    
    Args:
        chat_messages_store: dict[session_id, list[message]]
        time_filter: periodo dati da considerare
        
    Returns:
        Lista distribution per 12 slot orari (0-1, 2-3, ... 22-23)
    """
    # Filtro temporale
    cutoff = _get_time_cutoff(time_filter)
    
    hour_counts = defaultdict(int)
    
    for messages in chat_messages_store.values():
        for msg in messages:
            if msg.get("role") != "user":
                continue
            
            timestamp_str = msg.get("created_at")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if cutoff and timestamp < cutoff:
                    continue
                
                # Slot 2h: 0-1, 2-3, etc.
                hour_slot = (timestamp.hour // 2) * 2
                hour_counts[hour_slot] += 1
            except Exception:
                continue
    
    return [
        TemporalDistribution(
            hour_slot=slot,
            query_count=hour_counts.get(slot, 0),
            label=f"{slot:02d}:00-{(slot+1):02d}:59"  # Backend-generated label (i18n source)
        )
        for slot in range(0, 24, 2)
    ]


def aggregate_quality_metrics(
    chat_messages_store: dict
) -> QualityMetrics:
    """
    Aggrega metriche qualità risposte.
    
    Calcola:
    - Lunghezza media risposte assistant
    - Chunk utilizzati per risposta (da metadata)
    """
    response_lengths = []
    chunks_per_response = []
    
    for messages in chat_messages_store.values():
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            
            # Lunghezza risposta
            content = msg.get("content", "")
            response_lengths.append(len(content))
            
            # Chunk utilizzati (da metadata chunk_ids)
            chunk_ids = msg.get("chunk_ids", [])
            if chunk_ids:
                chunks_per_response.append(len(chunk_ids))
    
    avg_length = int(sum(response_lengths) / len(response_lengths)) if response_lengths else 0
    avg_chunks = sum(chunks_per_response) / len(chunks_per_response) if chunks_per_response else 0.0
    
    chunks_distribution = {
        "min": min(chunks_per_response) if chunks_per_response else 0,
        "max": max(chunks_per_response) if chunks_per_response else 0,
        "median": int(_percentile(chunks_per_response, 50.0)) if chunks_per_response else 0
    }
    
    return QualityMetrics(
        avg_response_length_chars=avg_length,
        avg_chunks_per_response=avg_chunks,
        chunks_distribution=chunks_distribution
    )


def get_assistant_id_for_user_message(messages: list, user_msg_index: int) -> str | None:
    """
    Trova il backend message_id del corrispondente assistant message.
    
    Args:
        messages: Lista completa dei messaggi della sessione
        user_msg_index: Indice del messaggio user nella lista
    
    Returns:
        Backend message_id del prossimo assistant message, o None se non trovato
    
    Note:
        - Utility centralizzata per evitare duplicazione logica (TECH-001)
        - Assume pattern standard: user → assistant (può avere system messages in mezzo)
    """
    # Cerca il prossimo assistant message dopo l'user message specificato
    for i in range(user_msg_index + 1, len(messages)):
        msg = messages[i]
        if msg.get("role") == "assistant":
            return msg.get("id")
    return None


def aggregate_problematic_queries(
    chat_messages_store: dict,
    feedback_store: dict,
    limit: int = 5
) -> ProblematicQueriesResponse:
    """
    Identifica query con feedback negativo ripetuto.
    
    Returns:
        ProblematicQueriesResponse con top 5 query + total_count (AC3)
    """
    # Mappa message_id -> query_text
    # ✅ Fix: Usa backend message_id dell'assistant message (non frontend local ID)
    message_to_query = {}
    for session_id, messages in chat_messages_store.items():
        for idx, msg in enumerate(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "").strip().lower()
                # Ottieni backend message_id del corrispondente assistant message
                assistant_msg_id = get_assistant_id_for_user_message(messages, idx)
                if assistant_msg_id:
                    message_to_query[assistant_msg_id] = user_query
    
    # Conteggio feedback negativi per query
    negative_counts = Counter()
    query_first_seen = {}
    
    for key, feedback in feedback_store.items():
        if feedback.get("vote") != "down":
            continue
        
        # key format: "{session_id}:{message_id}"
        message_id = key.split(":")[-1]
        query_text = message_to_query.get(message_id)
        
        if query_text:
            negative_counts[query_text] += 1
            if query_text not in query_first_seen:
                # ✅ Fix: Backend salva come "created_at" non "timestamp"
                query_first_seen[query_text] = feedback.get("created_at", "")
    
    top_queries = [
        ProblematicQuery(
            query_text=query,
            negative_feedback_count=count,
            first_seen=query_first_seen.get(query, "")
        )
        for query, count in negative_counts.most_common(limit)
    ]
    
    result = ProblematicQueriesResponse(
        queries=top_queries,
        total_count=len(negative_counts)  # AC3: Total problematic queries count
    )
    
    # ✅ Logging diagnostico (OPS-001): Warning se feedback presente ma aggregazione ritorna 0
    if len(feedback_store) > 0 and result.total_count == 0:
        # Conta quanti feedback negativi ci sono nello store
        negative_feedback_count = sum(1 for f in feedback_store.values() if f.get("vote") == "down")
        if negative_feedback_count > 0:
            log.warning(
                f"⚠️ Feedback store ha {negative_feedback_count} feedback negativi ma "
                f"aggregate_problematic_queries ritorna 0 risultati - verificare message ID pairing"
            )
    
    return result


def aggregate_engagement_stats(
    chat_messages_store: dict,
    feedback_store: dict
) -> EngagementStats:
    """
    Calcola engagement metrics.
    """
    session_durations = []
    queries_per_session = []
    total_queries_with_feedback = 0
    total_queries = 0
    
    for session_id, messages in chat_messages_store.items():
        if not messages:
            continue
        
        # Conteggio query sessione
        user_messages = [m for m in messages if m.get("role") == "user"]
        queries_count = len(user_messages)
        queries_per_session.append(queries_count)
        total_queries += queries_count
        
        # Durata sessione (primo - ultimo messaggio)
        try:
            timestamps = [
                datetime.fromisoformat(m.get("created_at").replace('Z', '+00:00'))
                for m in messages
                if m.get("created_at")
            ]
            if len(timestamps) >= 2:
                duration_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60
                session_durations.append(duration_minutes)
        except Exception:
            pass
        
        # Query con feedback
        # ✅ Fix: Usa backend message_id dell'assistant message
        # ✅ Performance: Pre-costruisce set di chiavi esatte per O(1) lookup (evita O(n*m) substring scan)
        session_feedback_keys = {
            key for key in feedback_store.keys() 
            if key.startswith(f"{session_id}:")
        }
        
        for idx, msg in enumerate(messages):
            if msg.get("role") == "user":
                # Ottieni backend message_id del corrispondente assistant message
                assistant_msg_id = get_assistant_id_for_user_message(messages, idx)
                if assistant_msg_id:
                    feedback_key = f"{session_id}:{assistant_msg_id}"
                    if feedback_key in session_feedback_keys:  # O(1) lookup
                        total_queries_with_feedback += 1
    
    avg_duration = sum(session_durations) / len(session_durations) if session_durations else 0.0
    avg_queries = sum(queries_per_session) / len(queries_per_session) if queries_per_session else 0.0
    conversion_rate = total_queries_with_feedback / total_queries if total_queries > 0 else 0.0
    
    # ✅ Logging diagnostico (OPS-001): Warning se feedback presente ma conversion rate è 0
    if len(feedback_store) > 0 and total_queries_with_feedback == 0 and total_queries > 0:
        log.warning(
            f"⚠️ Feedback store ha {len(feedback_store)} feedback ma "
            f"aggregate_engagement_stats trova 0 query con feedback su {total_queries} totali - "
            f"verificare message ID pairing"
        )
    
    return EngagementStats(
        avg_session_duration_minutes=avg_duration,
        avg_queries_per_session=avg_queries,
        feedback_conversion_rate=conversion_rate
    )


def aggregate_top_chunks(
    chat_messages_store: dict,
    limit: int = 10
) -> ChunkRetrievalResponse:
    """
    Identifica chunk più recuperati.
    
    Nota: Richiede che chat_messages_store includa metadata chunk_ids e scores.
    
    Returns:
        ChunkRetrievalResponse con top 10 chunk + total_chunks_count (AC5)
    """
    chunk_retrieval_counts = Counter()
    chunk_similarity_scores = defaultdict(list)
    chunk_documents = {}
    
    for messages in chat_messages_store.values():
        for msg in messages:
            if msg.get("role") != "assistant":
                continue
            
            chunk_ids = msg.get("chunk_ids", [])
            chunk_scores = msg.get("chunk_scores", [])
            chunk_docs = msg.get("chunk_documents", [])
            
            for i, chunk_id in enumerate(chunk_ids):
                chunk_retrieval_counts[chunk_id] += 1
                
                if i < len(chunk_scores):
                    chunk_similarity_scores[chunk_id].append(chunk_scores[i])
                
                if i < len(chunk_docs) and chunk_id not in chunk_documents:
                    chunk_documents[chunk_id] = chunk_docs[i]
    
    top_chunks = [
        ChunkRetrievalStat(
            chunk_id=chunk_id,
            document_id=chunk_documents.get(chunk_id, "unknown"),
            retrieval_count=count,
            avg_similarity_score=sum(chunk_similarity_scores[chunk_id]) / len(chunk_similarity_scores[chunk_id])
                if chunk_similarity_scores[chunk_id] else 0.0
        )
        for chunk_id, count in chunk_retrieval_counts.most_common(limit)
    ]
    
    return ChunkRetrievalResponse(
        top_chunks=top_chunks,
        total_chunks_count=len(chunk_retrieval_counts)  # AC5: Total unique chunks used
    )

