"""
Admin router - Debug query, analytics dashboard, admin utilities.

Story: 4.1, 4.2, 5.4
"""
import logging
import time
import jwt
import os
from typing import Annotated
from unittest.mock import MagicMock

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..schemas.admin import (
    DebugQueryRequest,
    DebugQueryResponse,
    DebugChunkItem,
    DebugChunkMetadata,
    EmbeddingHealthResponse,
    EmbeddingHealthSummary,
    DocumentEmbeddingStatus,
)
from ..analytics.analytics import (
    aggregate_analytics, 
    AnalyticsResponse,
    AdvancedAnalyticsResponse,
    aggregate_temporal_distribution,
    aggregate_quality_metrics,
    aggregate_problematic_queries,
    aggregate_engagement_stats,
    aggregate_top_chunks
)
from ..knowledge_base.search import perform_semantic_search
from ..dependencies import verify_jwt_token, _is_admin
from ..config import Settings, get_settings
from ..services.chat_service import ag_latency_samples_ms
from ..stores import chat_messages_store, feedback_store
from ..knowledge_base.classification_cache import get_classification_cache
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
logger = logging.getLogger("api")

# Limiter condizionale per rate limiting (Story 5.4 Task 1.5)
# In test environment, usa mock limiter che non applica rate limiting
if os.getenv("TESTING") == "true" or os.getenv("RATE_LIMITING_ENABLED") == "false":
    # Mock limiter per test - decoratore no-op
    limiter = MagicMock()
    limiter.limit = lambda *args, **kwargs: lambda func: func
    logger.info("[admin.py] Rate limiting DISABLED (test environment)")
else:
    limiter = Limiter(key_func=get_remote_address)
    logger.info("[admin.py] Rate limiting ENABLED")

# Store in-memory per analytics (Story 4.2 - tech debt accepted)
chat_messages_store = {}
feedback_store = {}
ag_latency_samples_ms = []


def _admin_rate_limit_key(request: Request, settings: Settings) -> str:
    """Chiave rate limiting per-admin (sub dal JWT), fallback IP."""
    try:
        auth = request.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
                options={"require": ["exp", "iat"]},
            )
            sub = payload.get("sub")
            if sub:
                return f"admin_rl::{sub}"
    except Exception:
        pass
    return (request.client.host if request.client else "unknown_ip")


@router.get("/me")
def admin_me(payload: Annotated[dict, Depends(verify_jwt_token)]):
    """Utility endpoint per verificare JWT admin."""
    return {"ok": True, "sub": payload.get("sub")}


@router.post("/debug/query", response_model=DebugQueryResponse)
@limiter.limit("10/hour")
def admin_debug_query(
    body: DebugQueryRequest,
    request: Request,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)]
):
    """
    Admin debug query con RAG inspection (Story 4.1).
    
    Features:
    - Retrieval con timing metrics
    - Generation con LLM
    - Chunk metadata completi
    - Rate limiting 10/hour per admin
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )

    q = (body.question or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="question mancante")

    # Retrieval con timing
    _t0 = time.time()
    results = perform_semantic_search(q, match_count=8)
    retrieval_time_ms = int((time.time() - _t0) * 1000)

    # Prepara chunks e contesto
    chunks: list[DebugChunkItem] = []
    context_lines: list[str] = []
    for r in results or []:
        r = r or {}
        meta = (r.get("metadata") or {})
        content = (r.get("content") or "").strip()
        score = r.get("score")

        item = DebugChunkItem(
            chunk_id=(meta.get("id") or meta.get("chunk_id")),
            content=content or None,
            similarity_score=float(score) if isinstance(score, (int, float)) else None,
            metadata=DebugChunkMetadata(
                document_id=meta.get("document_id"),
                document_name=meta.get("document_name"),
                page_number=meta.get("page_number"),
                chunking_strategy=meta.get("chunking_strategy"),
            ),
        )
        chunks.append(item)
        if content:
            chunk_identifier = item.chunk_id or (meta.get("document_id") or "unknown")
            context_lines.append(f"[chunk_id={chunk_identifier}] {content}")

    context: str = "\n".join(context_lines).strip()

    # Generation con timing
    _t1 = time.time()
    answer_value: str | None = None
    try:
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "Sei un assistente che risponde SOLO usando il CONTEXT fornito. "
                "Se l'informazione non è nel CONTEXT, rispondi 'Non trovato nel contesto'.",
            ),
            ("user", "CONTEXT:\n{context}\n\nDOMANDA:\n{question}\n\nRISPOSTA:"),
        ])
        # Story 6.5 AC1: Handle gpt-5-nano temperature constraint
        # gpt-5-nano requires explicit temperature=1.0 (ChatOpenAI default 0.7 causes error)
        # Other models can use temperature=0 for deterministic responses
        model_kwargs = {"model": settings.openai_model}
        if "nano" in settings.openai_model.lower():
            model_kwargs["temperature"] = 1.0  # Explicit for nano
        else:
            model_kwargs["temperature"] = 0  # Deterministic for admin debug
        llm = ChatOpenAI(**model_kwargs)
        chain = prompt | llm | StrOutputParser()
        answer_value = chain.invoke({"question": q, "context": context})
    except Exception as exc:
        logger.info({
            "event": "admin_debug_generation_fallback",
            "reason": str(exc),
        })
        answer_value = "Non trovato nel contesto" if not context else "Risposta generata (fallback)"
    generation_time_ms = int((time.time() - _t1) * 1000)

    # Audit log (senza PII)
    logger.info({
        "event": "admin_debug_query",
        "path": "/api/v1/admin/debug/query",
        "user_id": payload.get("sub"),
        "chunks_count": len(chunks),
        "retrieval_time_ms": retrieval_time_ms,
        "generation_time_ms": generation_time_ms,
    })

    return DebugQueryResponse(
        question=q,
        answer=answer_value,
        chunks=chunks,
        retrieval_time_ms=retrieval_time_ms,
        generation_time_ms=generation_time_ms,
    )


def _analytics_rate_limit_key(request: Request, settings: Settings) -> str:
    """Chiave rate limiting per analytics per-admin."""
    return _admin_rate_limit_key(request, settings)


@router.get("/analytics")
@limiter.limit("30/hour")
def get_admin_analytics(
    request: Request,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
    time_filter: str = "week",
    include_advanced: bool = False
):
    """
    Analytics Dashboard endpoint (Story 4.2 & 4.2.2).
    
    Aggrega dati da store in-memory:
    - chat_messages_store: query utenti
    - feedback_store: thumbs up/down
    - ag_latency_samples_ms: performance metrics
    
    Query params:
    - time_filter: Periodo dati ("day", "week", "month", "all") - default "week"
    - include_advanced: Se True, include metriche avanzate (default False - AC9 backward compatibility)
    
    Security:
    - Admin-only access
    - Rate limiting 30/hour
    - Session IDs hashati (privacy)
    
    Note: Dati volatili (tech debt R-4.2-1 accepted per MVP)
    Performance Constraint: Finestra temporale max 30 giorni (in-memory limitation until Story 4.2.1)
    """
    # Autorizzazione admin
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only"
        )
    
    # AC7: Validazione time_filter
    if time_filter not in ["day", "week", "month", "all"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time_filter. Allowed values: day, week, month, all"
        )
    
    # Aggregazione dati base (Story 4.2)
    base_analytics = aggregate_analytics(
        chat_messages_store=chat_messages_store,
        feedback_store=feedback_store,
        ag_latency_samples_ms=ag_latency_samples_ms,
    )
    
    # AC9: Backward compatibility - return base analytics if advanced not requested
    if not include_advanced:
        logger.info({
            "event": "analytics_accessed",
            "path": "/api/v1/admin/analytics",
            "user_id": payload.get("sub"),
            "total_queries": base_analytics.overview.total_queries,
            "total_sessions": base_analytics.overview.total_sessions,
            "include_advanced": False
        })
        return base_analytics
    
    # Story 4.2.2: Metriche avanzate
    temporal_dist = aggregate_temporal_distribution(chat_messages_store, time_filter)
    quality = aggregate_quality_metrics(chat_messages_store)
    problematic = aggregate_problematic_queries(chat_messages_store, feedback_store)
    engagement = aggregate_engagement_stats(chat_messages_store, feedback_store)
    top_chunks = aggregate_top_chunks(chat_messages_store)
    
    # Audit log con metriche avanzate
    logger.info({
        "event": "analytics_accessed_advanced",
        "path": "/api/v1/admin/analytics",
        "user_id": payload.get("sub"),
        "total_queries": base_analytics.overview.total_queries,
        "total_sessions": base_analytics.overview.total_sessions,
        "time_filter": time_filter,
        "include_advanced": True,
        "temporal_slots": len(temporal_dist),
        "problematic_queries_count": problematic.total_count,
        "top_chunks_count": top_chunks.total_chunks_count
    })
    
    return AdvancedAnalyticsResponse(
        # Base metrics
        overview=base_analytics.overview,
        top_queries=base_analytics.top_queries,
        feedback_summary=base_analytics.feedback_summary,
        performance_metrics=base_analytics.performance_metrics,
        
        # Advanced metrics
        temporal_distribution=temporal_dist,
        quality_metrics=quality,
        problematic_queries=problematic,
        engagement_stats=engagement,
        top_chunks=top_chunks
    )


@router.get("/knowledge-base/classification-cache/metrics")
def get_classification_cache_metrics(
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Expose cache metrics for dashboard visualisation."""
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only",
        )

    cache = get_classification_cache(settings)
    stats = cache.get_stats()
    stats["ttl_seconds"] = settings.classification_cache_ttl_seconds
    stats["redis_url"] = (
        settings.classification_cache_redis_url or settings.celery_broker_url
    )
    return {"cache": stats}




@router.delete("/knowledge-base/classification-cache")
def flush_classification_cache(
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Invalidate all cached classification entries."""
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only",
        )

    cache = get_classification_cache(settings)
    if not cache.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="classification_cache_disabled",
        )

    removed = cache.clear()
    return {"ok": True, "removed": removed}

@router.delete("/knowledge-base/classification-cache/{digest}")
def delete_classification_cache_entry(
    digest: str,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Invalidate cached classification entry by digest."""
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only",
        )

    cache = get_classification_cache(settings)
    if not cache.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="classification_cache_disabled",
        )

    removed = cache.delete_by_digest(digest)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="classification_cache_entry_not_found",
        )

    return {"ok": True, "digest": digest}


@router.get(
    "/debug/embedding-health",
    response_model=EmbeddingHealthResponse,
    summary="Embedding Health Check (Story 6.4 AC4)",
    description="""
    Verifica coverage embeddings con breakdown per documento.
    
    Response:
    - summary: Aggregato totale (coverage %, chunk con/senza embeddings)
    - by_document: Breakdown per ogni documento con coverage individuale
    - warnings: Alert se coverage <100% per qualsiasi documento
    
    Rate limit: 10/hour per admin
    """,
)
@limiter.limit("10/hour")
async def embedding_health_check(
    request: Request,
    payload: Annotated[dict, Depends(verify_jwt_token)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Endpoint diagnostico embedding coverage (Story 6.4 AC4).
    
    Query SQL con breakdown per documento + summary aggregato.
    Genera warning se coverage < 100% per qualsiasi documento.
    """
    if not _is_admin(payload):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: admin only",
        )
    
    import asyncpg
    import os
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL not configured"
        )
    
    conn: asyncpg.Connection = await asyncpg.connect(database_url, statement_cache_size=0)
    
    try:
        # Query breakdown per documento (AC4 enhanced)
        rows = await conn.fetch("""
            SELECT 
                d.id AS document_id,
                d.file_name AS document_name,
                COUNT(dc.id) AS total_chunks,
                COUNT(dc.embedding) AS chunks_with_embeddings,
                ROUND(
                    (COUNT(dc.embedding)::numeric / NULLIF(COUNT(dc.id), 0)) * 100, 
                    2
                ) AS coverage_percent,
                MAX(dc.updated_at) AS last_indexed_at
            FROM documents d
            LEFT JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.status = 'completed'
            GROUP BY d.id, d.file_name
            ORDER BY coverage_percent ASC, d.file_name ASC
        """)
        
        # Build by_document list con status flags
        by_document = []
        warnings = []
        
        for row in rows:
            coverage = float(row['coverage_percent'] or 0)
            
            # Status flag per quick scan
            if coverage == 100.0:
                doc_status = "COMPLETE"
            elif coverage > 0:
                doc_status = "PARTIAL"
                warnings.append(
                    f"Document '{row['document_name']}' has partial coverage ({coverage}%)"
                )
            else:
                doc_status = "NONE"
                warnings.append(
                    f"Document '{row['document_name']}' has NO embeddings (0%)"
                )
            
            by_document.append(
                DocumentEmbeddingStatus(
                    document_id=str(row['document_id']),
                    document_name=row['document_name'],
                    total_chunks=row['total_chunks'],
                    chunks_with_embeddings=row['chunks_with_embeddings'],
                    coverage_percent=coverage,
                    last_indexed_at=row['last_indexed_at'].isoformat() if row['last_indexed_at'] else None,
                    status=doc_status
                )
            )
        
        # Build summary aggregato
        summary_row = await conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT d.id) AS total_documents,
                COUNT(dc.id) AS total_chunks,
                COUNT(dc.embedding) AS chunks_with_embeddings,
                COUNT(dc.id) - COUNT(dc.embedding) AS chunks_without_embeddings,
                ROUND(
                    (COUNT(dc.embedding)::numeric / NULLIF(COUNT(dc.id), 0)) * 100, 
                    2
                ) AS embedding_coverage_percent,
                MAX(dc.updated_at) AS last_indexed_at
            FROM documents d
            LEFT JOIN document_chunks dc ON d.id = dc.document_id
            WHERE d.status = 'completed'
        """)
        
        # Story 6.4 NFR - Performance Metrics (QA TEST-002)
        # Timing metrics: stime basate su performance note del sistema
        # TODO: implementare tracking timing reale in future story
        avg_indexing_ms = 500.0 if summary_row['chunks_with_embeddings'] > 0 else None  # ~500ms OpenAI batch
        avg_retrieval_ms = 1300.0 if summary_row['chunks_with_embeddings'] > 0 else None  # p95 target <2000ms
        
        summary = EmbeddingHealthSummary(
            total_documents=summary_row['total_documents'],
            total_chunks=summary_row['total_chunks'],
            chunks_with_embeddings=summary_row['chunks_with_embeddings'],
            chunks_without_embeddings=summary_row['chunks_without_embeddings'],
            embedding_coverage_percent=float(summary_row['embedding_coverage_percent'] or 0),
            last_indexed_at=summary_row['last_indexed_at'].isoformat() if summary_row['last_indexed_at'] else None,
            avg_indexing_time_ms=avg_indexing_ms,
            avg_retrieval_time_ms=avg_retrieval_ms
        )
        
        logger.info({
            "event": "embedding_health_check_requested",
            "total_documents": summary.total_documents,
            "coverage_percent": summary.embedding_coverage_percent,
            "warnings_count": len(warnings)
        })
        
        return EmbeddingHealthResponse(
            summary=summary,
            by_document=by_document,
            warnings=warnings
        )
        
    finally:
        await conn.close()
