"""
Chat router - Gestisce query semantica, augmented generation, feedback.

Endpoints:
- POST /api/v1/chat/query - Semantic search query (Story 3.1)
- POST /api/v1/chat/sessions/{sessionId}/messages - Augmented generation (Story 3.2)
- POST /api/v1/chat/messages/{messageId}/feedback - User feedback (Story 3.4)

Stories: 3.1, 3.2, 3.4
"""
import time
import logging
import hashlib
from typing import Annotated, Optional, Dict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Query, Response
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import Runnable

from ..schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ChatQueryChunk,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    CitationItem,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    ChatRequest,  # Story 5.5 Task 3: Chat endpoint schema
    ChatResponse,  # Story 5.5 Task 3: Chat endpoint schema
    SessionHistoryResponse,  # Story 9.2
    ConversationMessage as ConversationMessageSchema,  # Story 9.2
)
from ..config import Settings, get_settings
from ..services.chat_service import record_ag_latency_ms, get_llm
from ..services.rate_limit_service import rate_limit_service
from ..services.conversation_service import get_conversation_manager  # Story 7.1
from ..services.persistence_service import ConversationPersistenceService  # Story 9.2
from ..dependencies import _auth_bridge, TokenPayload, get_supabase_client  # Story 4.2.4
from .. import database  # Story 9.2
from ..knowledge_base.search import perform_semantic_search
from ..knowledge_base.enhanced_retrieval import get_enhanced_retriever  # Story 7.2
from ..knowledge_base.dynamic_retrieval import get_dynamic_strategy  # Story 7.2
from ..models.answer_with_citations import AnswerWithCitations
from ..models.enhanced_response import EnhancedAcademicResponse  # Story 7.1
from ..prompts.academic_medical import (  # Story 7.1
    BASELINE_PROMPT,
    ACADEMIC_MEDICAL_SYSTEM_PROMPT,
)
from ..stores import chat_messages_store  # feedback_store deprecato Story 4.2.4
from ..repositories.feedback_repository import FeedbackRepository  # Story 4.2.4

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
logger = logging.getLogger("api")


def _resolve_chat_rate_limit_key(request: Request, payload: TokenPayload) -> str:
    """
    Determina la chiave per il rate limiting della chat.

    Prioritizza l'identificativo utente; fallback sull'IP origine.
    """
    if isinstance(payload, dict):
        sub = payload.get("sub")
        if sub:
            return f"user::{sub}"

    if request.client and request.client.host:
        return f"ip::{request.client.host}"

    return "anonymous"


def _build_fallback_answer(chunks: list[ChatQueryChunk]) -> str:
    """
    Costruisce una risposta di fallback basata sui chunk recuperati.

    Args:
        chunks: Lista di chunk di contesto disponibili

    Returns:
        stringa con estratti rilevanti oppure messaggio di contesto mancante
    """
    snippets: list[str] = []
    for chunk in chunks:
        if not chunk or not chunk.content:
            continue
        text = chunk.content.strip()
        if not text:
            continue
        shortened = text if len(text) <= 320 else f"{text[:317]}..."
        document_ref = f"(documento: {chunk.document_id})" if chunk.document_id else ""
        snippets.append(f"- {shortened} {document_ref}".strip())
        if len(snippets) >= 3:
            break

    if not snippets:
        return "Contesto non sufficiente per generare una risposta. Riprovare con una domanda diversa."

    header = (
        "Al momento non posso generare una sintesi completa, ma ecco gli estratti più pertinenti "
        "trovati nella knowledge base:"
    )
    return "\n".join([header, *snippets])


@router.post("/query", response_model=ChatQueryResponse)
def chat_query_endpoint(
    body: ChatQueryRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Semantic search query endpoint (Story 3.1).
    
    Esegue ricerca semantica sui chunk indicizzati e restituisce
    risultati con similarity scores.
    
    Args:
        body: Query request con question e parametri ricerca
        request: FastAPI Request
        payload: JWT payload verificato
        
    Returns:
        ChatQueryResponse con lista chunk rilevanti
        
    Security:
        - JWT authentication required
        - Rate limiting: 60/minute (gestito da SlowAPI su main.app)
    """
    results = perform_semantic_search(
        body.question,
        body.match_count,
        body.match_threshold,
    )

    chunks: list[dict] = []
    for r in results:
        payload = r or {}
        metadata = payload.get("metadata") or {}
        score = payload.get("similarity_score")
        if score is None:
            score = payload.get("score")
        chunk_id = (
            metadata.get("id")
            or metadata.get("chunk_id")
            or metadata.get("document_chunk_id")
            or payload.get("id")
        )
        document_id = metadata.get("document_id") or payload.get("document_id")
        chunks.append({
            "id": str(chunk_id) if chunk_id else None,
            "document_id": str(document_id) if document_id else None,
            "content": payload.get("content"),
            "similarity": float(score) if isinstance(score, (int, float)) else None,
        })
    
    return ChatQueryResponse(chunks=[ChatQueryChunk(**c) for c in chunks])


@router.get("/sessions/{sessionId}/history/full", response_model=SessionHistoryResponse)
async def get_session_history(
    sessionId: str,
    request: Request,
    response: Response,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Session history retrieval endpoint (Story 9.2).
    
    Recupera full conversational history per session da database con pagination.
    
    Features:
    - Pagination con limit/offset parameters
    - Rate limiting: 60 req/min per session
    - Feature flag: ENABLE_PERSISTENT_MEMORY
    - Graceful degradation: 404 per session nuova
    
    Args:
        sessionId: Session identifier
        request: FastAPI Request
        response: FastAPI Response (per headers)
        limit: Max messaggi per page (default 100, max 500)
        offset: Pagination offset (default 0)
        payload: JWT payload verificato
        settings: Application settings
        
    Returns:
        SessionHistoryResponse con messages, total_count, has_more
        
    Security:
        - JWT authentication required
        - Rate limiting: 60/minute
        - Cache-Control: private, max-age=0, no-store (per-user data)
    """
    # QA Must-Fix: Cache-Control headers per evitare caching proxy indesiderato
    response.headers["Cache-Control"] = "private, max-age=0, no-store"
    response.headers["Pragma"] = "no-cache"
    
    # AC6: Feature flag check
    if not settings.enable_persistent_memory:
        logger.info({
            "event": "history_disabled_feature_flag",
            "session_id": sessionId,
        })
        # Graceful degradation: return empty history
        return SessionHistoryResponse(
            messages=[],
            total_count=0,
            has_more=False,
        )
    
    # AC1: Rate limiting enforcement
    rate_limit_service.enforce_rate_limit(
        key=_resolve_chat_rate_limit_key(request, payload),
        scope="session_history",
        window_seconds=60,
        max_requests=60,
    )
    
    if not sessionId or not sessionId.strip():
        raise HTTPException(status_code=400, detail="sessionId mancante")
    
    # AC7: Error handling con graceful degradation
    if not database.db_pool:
        logger.warning({
            "event": "history_unavailable_no_db_pool",
            "session_id": sessionId,
        })
        # AC7: Graceful degradation se DB non disponibile
        return SessionHistoryResponse(
            messages=[],
            total_count=0,
            has_more=False,
        )
    
    try:
        # AC2: Use ConversationPersistenceService.load_session_history()
        persistence_service = ConversationPersistenceService(database.db_pool)
        
        # Load messages con pagination
        conversation_messages = await persistence_service.load_session_history(
            session_id=sessionId,
            limit=limit + 1,  # Fetch +1 per determinare has_more
            offset=offset,
        )
        
        # AC1: Determine has_more based su limit+1 fetch
        has_more = len(conversation_messages) > limit
        if has_more:
            conversation_messages = conversation_messages[:limit]
        
        # AC7: Return empty array per sessione nuova/vuota (NOT 404)
        if not conversation_messages and offset == 0:
            logger.info({
                "event": "session_history_empty",
                "session_id": sessionId,
            })
            return SessionHistoryResponse(
                messages=[],
                total_count=0,
                has_more=False,
            )
        
        # AC5: Convert to response schema preservando formato identico
        response_messages: list[ConversationMessageSchema] = []
        for msg in conversation_messages:
            # Generate unique message ID from timestamp + content hash
            msg_id = hashlib.sha256(
                f"{sessionId}_{msg.timestamp.isoformat()}_{msg.content[:50]}".encode()
            ).hexdigest()[:16]
            
            # CRITICAL FIX: Popola metadata con citations per frontend
            # Frontend cerca msg.metadata.citations per rendering popover
            metadata_dict = {}
            if msg.chunk_ids:
                metadata_dict["citations"] = [
                    {"chunk_id": cid} for cid in msg.chunk_ids
                ]
            
            response_messages.append(
                ConversationMessageSchema(
                    id=msg_id,
                    role=msg.role,  # type: ignore[arg-type]
                    content=msg.content,
                    source_chunk_ids=msg.chunk_ids,
                    metadata=metadata_dict,
                    created_at=msg.timestamp.isoformat(),
                )
            )
        
        # AC1: Calcola total_count (approximation basata su has_more)
        # In produzione, considerare COUNT(*) separata per total_count esatto
        total_count = offset + len(response_messages)
        if has_more:
            total_count += 1  # At least 1 more
        
        logger.info({
            "event": "session_history_retrieved",
            "session_id": sessionId,
            "messages_count": len(response_messages),
            "has_more": has_more,
            "limit": limit,
            "offset": offset,
        })
        
        return SessionHistoryResponse(
            messages=response_messages,
            total_count=total_count,
            has_more=has_more,
        )
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error({
            "event": "session_history_error",
            "session_id": sessionId,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }, exc_info=True)
        # AC7: 500 error con graceful handling
        raise HTTPException(
            status_code=500,
            detail="Failed to load session history"
        )


@router.post("/sessions/{sessionId}/messages", response_model=ChatMessageCreateResponse)
async def create_chat_message(
    sessionId: str,
    body: ChatMessageCreateRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    Augmented generation endpoint (Story 3.2 / 2.11).
    
    Genera risposta usando LLM con contesto fornito dai chunk.
    Implementa:
    - Context-aware generation con vincolo uso esclusivo contesto
    - Citation tracking con chunk IDs
    - Performance metrics (latency, p95)
    - Fallback sicuro per ambienti senza LLM
    
    Args:
        sessionId: Session identifier
        body: Request con messaggio utente, configurazione retrieval e chunk opzionali
        request: FastAPI Request
        payload: JWT payload verificato
        
    Returns:
        ChatMessageCreateResponse con risposta, citazioni, message_id
        
    Security:
        - JWT authentication required
        - Rate limiting: 60/minute (gestito da SlowAPI su main.app)
    """
    _ag_start_time = time.time()

    rate_limit_service.enforce_rate_limit(
        key=_resolve_chat_rate_limit_key(request, payload),
        scope="chat_message",
        window_seconds=settings.chat_rate_limit_window_sec,
        max_requests=settings.chat_rate_limit_max_requests,
    )

    if not sessionId or not sessionId.strip():
        raise HTTPException(status_code=400, detail="sessionId mancante")
    user_message = (body.message or "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="message mancante")

    logger.info({
        "event": "ag_message_request",
        "path": f"/api/v1/chat/sessions/{sessionId}/messages",
        "session_id": sessionId,
        "has_chunks": bool(body.chunks),
        "match_count": body.match_count,
        "match_threshold": body.match_threshold,
    })

    # Recupera chunk: usa payload client oppure esegue semantic search server-side
    retrieval_time_ms = 0
    resolved_chunks: list[ChatQueryChunk] = []
    if body.chunks:
        resolved_chunks = [chunk for chunk in body.chunks if chunk]
    else:
        retrieval_started_at = time.time()
        
        # Story 7.2 AC2: Dynamic match count (se enabled)
        effective_match_count = body.match_count
        if settings.enable_dynamic_match_count:
            try:
                dynamic_strategy = get_dynamic_strategy(settings)
                effective_match_count = dynamic_strategy.get_optimal_match_count(
                    query=user_message,
                    min_count=settings.dynamic_match_count_min,
                    max_count=settings.dynamic_match_count_max,
                    default_count=body.match_count,
                )
                logger.info({
                    "event": "dynamic_match_count_computed",
                    "query_preview": user_message[:100],
                    "original_count": body.match_count,
                    "computed_count": effective_match_count,
                })
            except Exception as exc:  # noqa: BLE001 - fallback a count originale
                logger.warning({
                    "event": "dynamic_match_count_failed",
                    "error": str(exc),
                    "fallback_count": body.match_count,
                })
                effective_match_count = body.match_count
        
        # Story 7.2 AC1: Enhanced retrieval con re-ranking (se enabled)
        try:
            if settings.enable_cross_encoder_reranking:
                # Use enhanced retrieval pipeline
                retriever = get_enhanced_retriever(settings)
                search_results = retriever.retrieve_and_rerank(
                    query=user_message,
                    match_count=effective_match_count,
                    match_threshold=body.match_threshold,
                    diversify=settings.enable_chunk_diversification,  # AC3: Diversification
                )
                logger.info({
                    "event": "enhanced_retrieval_used",
                    "session_id": sessionId,
                    "match_count": effective_match_count,
                    "diversify": settings.enable_chunk_diversification,
                })
            else:
                # Use baseline semantic search
                search_results = perform_semantic_search(
                    query=user_message,
                    match_count=effective_match_count,
                    match_threshold=body.match_threshold,
                )
        except Exception as exc:  # noqa: BLE001 - fallback a baseline
            logger.warning({
                "event": "enhanced_retrieval_fallback",
                "error": str(exc),
                "action": "use_baseline_search",
                "session_id": sessionId,
            })
            # Graceful degradation: fallback a baseline search
            try:
                search_results = perform_semantic_search(
                    query=user_message,
                    match_count=effective_match_count,
                    match_threshold=body.match_threshold,
                )
            except Exception as fallback_exc:  # noqa: BLE001
                logger.error({
                    "event": "semantic_search_error",
                    "error": str(fallback_exc),
                    "session_id": sessionId,
                })
                search_results = []
        
        retrieval_time_ms = int((time.time() - retrieval_started_at) * 1000)

        for item in search_results or []:
            metadata = (item or {}).get("metadata") or {}
            chunk_id_value = (
                metadata.get("id")
                or metadata.get("chunk_id")
                or metadata.get("document_chunk_id")
                or item.get("id")
            )
            document_id_value = metadata.get("document_id") or item.get("document_id")
            chunk_payload = {
                "id": str(chunk_id_value) if chunk_id_value else None,
                "document_id": str(document_id_value) if document_id_value else None,
                "content": item.get("content"),
                "similarity": item.get("similarity_score") or item.get("score"),
            }
            try:
                resolved_chunks.append(ChatQueryChunk(**chunk_payload))
            except Exception:
                logger.debug({
                    "event": "chunk_parse_skip",
                    "payload": chunk_payload,
                })

    logger.info({
        "event": "ag_chunks_resolved",
        "session_id": sessionId,
        "chunks_count": len(resolved_chunks),
        "retrieval_time_ms": retrieval_time_ms,
    })

    # Story 7.1: Load conversational context if enabled
    conversation_history = ""
    context_window = None
    if settings.enable_conversational_memory:
        conv_manager = get_conversation_manager(
            max_turns=settings.conversation_max_turns,
            max_tokens=settings.conversation_max_tokens,
            compact_length=settings.conversation_message_compact_length,
            enable_persistence=settings.enable_persistent_memory,  # Story 9.1 AC3
        )
        context_window = conv_manager.get_context_window(sessionId)
        conversation_history = conv_manager.format_for_prompt(context_window)
        
        logger.info({
            "event": "context_window_loaded",
            "session_id": sessionId,
            "messages_count": len(context_window.messages),
            "total_tokens": context_window.total_tokens,
        })
    else:
        conversation_history = "\n=== PRIMA INTERAZIONE (nessuna cronologia) ===\n"
    
    # Costruzione del contesto a partire dai chunk
    context_lines: list[str] = []
    for chunk in resolved_chunks:
        if not chunk:
            continue
        chunk_identifier = chunk.id or chunk.document_id or "unknown"
        chunk_content = (chunk.content or "").strip()
        if chunk_content:
            context_lines.append(f"[chunk_id={chunk_identifier}] {chunk_content}")
    context: str = "\n".join(context_lines).strip()
    
    # Story 7.1: Choose prompt and parser based on feature flags
    if settings.enable_enhanced_response_model:
        parser = PydanticOutputParser(pydantic_object=EnhancedAcademicResponse)
    else:
        parser = PydanticOutputParser(pydantic_object=AnswerWithCitations)
    
    format_instructions = parser.get_format_instructions()
    
    if settings.enable_academic_prompt:
        # Story 7.1 AC1: Academic medical prompt
        system_prompt = ACADEMIC_MEDICAL_SYSTEM_PROMPT
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{question}"),
        ]).partial(
            format_instructions=format_instructions,
            context=context,
            conversation_history=conversation_history,
        )
    else:
        # Baseline prompt (backward compatibility)
        system_prompt = BASELINE_PROMPT
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "CONTEXT:\n{context}\n\nDOMANDA:\n{question}"),
        ]).partial(format_instructions=format_instructions)

    message_id = str(uuid4())
    answer_value: Optional[str] = None
    citations_value: Optional[list[str]] = None
    generation_time_ms = 0

    if not context:
        answer_value = "Nessun contenuto rilevante trovato per la tua domanda."
        citations_value = []
        logger.warning({
            "event": "ag_no_context",
            "session_id": sessionId,
            "reason": "no_chunks_available",
        })
    else:
        try:
            llm = get_llm(settings)
            chain: Runnable = prompt | llm | parser
            gen_started_at = time.time()
            
            # Story 7.1: Invoke with appropriate parameters
            if settings.enable_academic_prompt:
                result = chain.invoke({
                    "question": user_message,
                })
            else:
                result = chain.invoke({
                    "question": user_message,
                    "context": context,
                })
            
            generation_time_ms = int((time.time() - gen_started_at) * 1000)
            
            # Story 7.1: Extract answer and citations based on model type
            if settings.enable_enhanced_response_model:
                # EnhancedAcademicResponse model
                answer_value = getattr(result, "spiegazione_dettagliata", None)
                if not answer_value:
                    # Fallback: build from all fields
                    parts = []
                    if hasattr(result, "introduzione") and result.introduzione:
                        parts.append(result.introduzione)
                    if hasattr(result, "concetti_chiave") and result.concetti_chiave:
                        parts.append("Concetti chiave: " + ", ".join(result.concetti_chiave))
                    if hasattr(result, "spiegazione_dettagliata") and result.spiegazione_dettagliata:
                        parts.append(result.spiegazione_dettagliata)
                    if hasattr(result, "note_cliniche") and result.note_cliniche:
                        parts.append("Note cliniche: " + result.note_cliniche)
                    answer_value = "\n\n".join(parts)
                
                # Extract citations from EnhancedAcademicResponse
                citations_metadata = getattr(result, "citazioni", [])
                citations_value = [c.chunk_id for c in citations_metadata if hasattr(c, "chunk_id")]
                
                # Log enhanced response metadata
                logger.info({
                    "event": "enhanced_response_generated",
                    "session_id": sessionId,
                    "has_clinical_notes": hasattr(result, "note_cliniche") and bool(result.note_cliniche),
                    "has_limitations": hasattr(result, "limitazioni_contesto") and bool(result.limitazioni_contesto),
                    "concepts_count": len(result.concetti_chiave) if hasattr(result, "concetti_chiave") else 0,
                    "citations_count": len(citations_value),
                    "confidenza": getattr(result, "confidenza_risposta", None),
                })
            else:
                # Baseline AnswerWithCitations model
                answer_value = getattr(result, "risposta", None)
                citations_value = getattr(result, "citazioni", None)
                
        except Exception as exc:  # noqa: BLE001 - fallback per ambienti senza LLM
            citations_value = []
            for chunk in resolved_chunks:
                if not chunk:
                    continue
                citations_value.append((chunk.id or chunk.document_id or "unknown"))
            answer_value = (
                "Non trovato nel contesto"
                if not context
                else _build_fallback_answer(resolved_chunks)
            )
            logger.info({
                "event": "ag_fallback",
                "reason": str(exc),
                "citations_count": len(citations_value),
            })

    answer_value = (answer_value or "").strip() or "Non trovato nel contesto"
    citations_value = citations_value or []

    # Arricchisci citazioni con metadati minimi per popover (prima di add_turn)
    enriched_citations: list[dict] = []
    chunks_by_id: Dict[str, ChatQueryChunk] = {}
    for ch in resolved_chunks:
        if ch and (ch.id or ch.document_id):
            chunks_by_id[(ch.id or ch.document_id)] = ch
    
    for cid in citations_value or []:
        ch = chunks_by_id.get(cid)
        excerpt_value: str | None = None
        document_id_value: str | None = None
        if ch:
            text = (ch.content or "").strip()
            if text:
                excerpt_value = text[:1000]
            document_id_value = ch.document_id
        enriched_citations.append({
            "chunk_id": cid,
            "document_id": document_id_value,
            "excerpt": excerpt_value,
            "position": None,
        })
    
    # Story 7.1: Save conversation turn if conversational memory enabled
    # CRITICAL FIX: conv_manager.add_turn() gestisce TUTTA la persistenza (L1+L2)
    # Rimuovere salvataggio duplicato per evitare messaggi duplicati
    if settings.enable_conversational_memory and context_window is not None:
        conv_manager = get_conversation_manager(
            max_turns=settings.conversation_max_turns,
            max_tokens=settings.conversation_max_tokens,
            compact_length=settings.conversation_message_compact_length,
            enable_persistence=settings.enable_persistent_memory,  # Story 9.1 AC3
        )
        
        # DIAGNOSTIC: Log manager type per verify HybridConversationManager initialization
        manager_type = type(conv_manager).__name__
        logger.info({
            "event": "conversation_manager_type",
            "manager_type": manager_type,
            "persistence_enabled": settings.enable_persistent_memory,
            "conversational_memory_enabled": settings.enable_conversational_memory,
        })
        
        # add_turn() salva ENTRAMBI i messaggi (user + assistant) in L1 cache
        # e avvia async persist in DB se HybridConversationManager
        conv_manager.add_turn(
            sessionId,
            user_message,
            answer_value,
            citations_value,  # Passa citations come chunk IDs
        )
        
        logger.info({
            "event": "conversation_turn_saved",
            "session_id": sessionId,
            "turn_number": len(chat_messages_store.get(sessionId, [])) // 2,
            "user_msg_length": len(user_message),
            "assistant_msg_length": len(answer_value),
            "citations_count": len(citations_value) if citations_value else 0,
            "manager_type": manager_type,
        })
    
    # Metriche di performance: latenza e p95 aggiornata
    _ag_duration_ms = int((time.time() - _ag_start_time) * 1000)
    metrics = record_ag_latency_ms(_ag_duration_ms)
    logger.info({
        "event": "ag_metrics",
        "latency_ms": _ag_duration_ms,
        "p50_ms": metrics.get("p50_ms"),
        "p95_ms": metrics.get("p95_ms"),
        "samples": metrics.get("count"),
        "session_id": sessionId,
        "retrieval_time_ms": retrieval_time_ms,
        "generation_time_ms": generation_time_ms,
    })
    
    return ChatMessageCreateResponse(
        message_id=message_id,
        message=answer_value,
        answer=answer_value,
        citations=[CitationItem(**c) for c in enriched_citations],
        retrieval_time_ms=retrieval_time_ms,
        generation_time_ms=generation_time_ms,
    )


@router.post("/messages/{messageId}/feedback", response_model=FeedbackCreateResponse)
async def create_feedback(
    messageId: str,
    body: FeedbackCreateRequest,
    request: Request,
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
    supabase_client: Annotated[any, Depends(get_supabase_client)],  # Story 4.2.4
):
    """
    User feedback endpoint (Story 3.4, migrated 4.2.4).
    
    Registra feedback thumbs up/down per messaggi generati con persistenza database.
    
    Features:
    - Validazione best-effort esistenza messaggio
    - Non blocca UX se messaggio non trovato
    - Persistenza Supabase PostgreSQL (Story 4.2.4)
    - UPSERT logic: secondo feedback aggiorna il precedente
    
    Args:
        messageId: Message identifier
        body: Feedback request con sessionId e vote
        request: FastAPI Request
        payload: JWT payload verificato
        supabase_client: Supabase client (injected)
        
    Returns:
        FeedbackCreateResponse con conferma
        
    Security:
        - JWT authentication required
        - Rate limiting: 60/minute (gestito da SlowAPI su main.app)
        
    Story 4.2.4: Migrated from in-memory feedback_store to database persistence.
    """
    if not messageId or not messageId.strip():
        raise HTTPException(status_code=400, detail="messageId mancante")
    if not body.sessionId or not body.sessionId.strip():
        raise HTTPException(status_code=400, detail="sessionId mancante")
    
    # Verifica esistenza messaggio nella sessione (best effort)
    found = False
    for m in chat_messages_store.get(body.sessionId, []) or []:
        if m and m.get("id") == messageId:
            found = True
            break
    if not found:
        # Non bloccare l'UX: accetta comunque ma logga warn
        logger.info({
            "event": "feedback_message_not_found",
            "session_id": body.sessionId,
            "message_id": messageId,
        })
    
    # Story 4.2.4: Persist feedback to database via repository
    repo = FeedbackRepository(supabase_client)
    
    try:
        await repo.create_feedback(
            session_id=body.sessionId,
            message_id=messageId,
            vote=body.vote,
            comment=body.comment,  # Story 5.5 Task 1: Commento opzionale
            user_id=payload.get("sub") if isinstance(payload, dict) else None,
            ip_address=request.client.host if request.client else None
        )
    except ValueError as e:
        # Validation error (invalid vote)
        logger.warning({
            "event": "feedback_validation_failed",
            "session_id": body.sessionId,
            "message_id": messageId,
            "error": str(e)
        })
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error({
            "event": "feedback_save_failed",
            "session_id": body.sessionId,
            "message_id": messageId,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(status_code=500, detail="Feedback save failed")
    
    # Success logging handled by repository
    return FeedbackCreateResponse(ok=True)


@router.post("", response_model=ChatResponse)
def chat_endpoint(
    body: ChatRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    payload: Annotated[TokenPayload, Depends(_auth_bridge)],
):
    """
    RAG Chat endpoint (Story 5.5 Task 3).
    
    Esegue semantic search e genera risposta con LLM.
    
    Features:
    - Semantic search sui chunk indicizzati
    - Generazione risposta con LLM
    - Tracking session_id
    
    Args:
        body: ChatRequest con message, session_id, match_count
        request: FastAPI Request
        payload: JWT payload verificato
        
    Returns:
        ChatResponse con answer, session_id, sources
        
    Security:
        - JWT authentication required
        - Rate limiting: 60/minute (gestito da SlowAPI su main.app)
    """
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="message mancante")
    if not body.session_id or not body.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id mancante")
    
    # Semantic search
    try:
        search_results = perform_semantic_search(
            query=body.message,
            match_count=body.match_count,
            match_threshold=body.match_threshold,
        )
    except Exception as e:
        logger.error({
            "event": "semantic_search_error",
            "error": str(e),
            "session_id": body.session_id,
        })
        search_results = []
    
    if not search_results:
        # Story 5.5 Task 3: Return 200 with empty answer instead of 404
        logger.warning({
            "event": "no_relevant_content",
            "query": body.message[:100],
            "session_id": body.session_id,
        })
        return ChatResponse(
            answer="Nessun contenuto rilevante trovato per la tua domanda.",
            session_id=body.session_id,
            sources=[]
        )
    
    # Prepara contesto per LLM
    context_lines = []
    sources = []
    for r in search_results:
        content = r.get("content", "")
        if content:
            context_lines.append(content)
            sources.append({
                "content": content[:200],  # Excerpt
                "metadata": r.get("metadata", {}),
                "similarity_score": r.get("similarity_score"),
            })
    
    context = "\n\n".join(context_lines)
    
    # Generazione risposta LLM
    try:
        llm = get_llm(settings)
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "Sei un assistente esperto in fisioterapia. Rispondi in italiano basandoti sul seguente contesto:\n\n{context}"),
            ("human", "{question}")
        ])
        
        chain = prompt_template | llm
        response = chain.invoke({"context": context, "question": body.message})
        
        # Extract answer from response
        if hasattr(response, "content"):
            answer = response.content
        elif isinstance(response, str):
            answer = response
        else:
            answer = str(response)
    
    except Exception as e:
        logger.error({
            "event": "llm_generation_error",
            "error": str(e),
            "session_id": body.session_id,
        })
        # Fallback: ritorna solo i chunk senza generazione
        answer = "Risposta non disponibile. Ecco i risultati della ricerca semantica."
    
    # Log evento
    logger.info({
        "event": "chat_query",
        "session_id": body.session_id,
        "query": body.message[:100],
        "sources_count": len(sources),
        "user_id": payload.get("sub") if isinstance(payload, dict) else None,
    })
    
    return ChatResponse(
        answer=answer,
        session_id=body.session_id,
        sources=sources
    )

