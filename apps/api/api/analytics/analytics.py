"""
Analytics Endpoint - Story 4.2
Endpoint: GET /api/v1/admin/analytics

Aggregazione dati da store in-memory per dashboard analytics.
Dati volatili (tech debt R-4.2-1 accepted).
"""

import hashlib
from collections import Counter
from typing import Annotated
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, status


router = APIRouter()


# -------------------------------
# Response Models
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


# -------------------------------
# Aggregation Functions
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

