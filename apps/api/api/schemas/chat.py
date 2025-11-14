"""
Chat schemas - Request/Response models per chat RAG system.

Story: 3.1, 3.2, 3.4
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, AliasChoices


# Story 3.1: Semantic Search
class ChatQueryRequest(BaseModel):
    """Request per query semantica chat."""
    sessionId: str
    question: str
    match_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    match_count: int = Field(default=8, ge=1, le=50)


class ChatQueryChunk(BaseModel):
    """Chunk risultato con similarity score."""
    id: Optional[str] = None
    document_id: Optional[str] = None
    content: Optional[str] = None
    similarity: Optional[float] = None


class ChatQueryResponse(BaseModel):
    """Response semantic search con chunks."""
    chunks: list[ChatQueryChunk]


# Story 3.2 / 2.11: Augmented Generation
class ChatMessageCreateRequest(BaseModel):
    """
    Request per creare messaggio chat con AG.

    Story 2.11 aggiorna il contratto per includere configurazioni di retrieval.
    """

    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(
        ...,
        validation_alias=AliasChoices("message", "question"),
        description="Messaggio dell'utente / domanda naturale",
    )
    match_count: int = Field(
        default=8,
        ge=1,
        le=50,
        description="Numero massimo di chunk da recuperare",
    )
    match_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Soglia di similarità (0-1). None => default modello",
    )
    chunks: Optional[list[ChatQueryChunk]] = Field(
        default=None,
        description=(
            "Chunk opzionali pre-calcolati dal client. "
            "Se assenti il backend esegue la semantic search."
        ),
    )


class CitationItem(BaseModel):
    """Citation item con metadati per source visualization."""
    chunk_id: str
    document_id: Optional[str] = None
    excerpt: Optional[str] = None
    position: Optional[int] = None


class ChatMessageCreateResponse(BaseModel):
    """Response messaggio generato con citazioni."""
    message_id: str
    message: Optional[str] = None  # Story 2.11: campo primario per risposta
    answer: Optional[str] = None
    citations: Optional[list[CitationItem]] = None
    retrieval_time_ms: Optional[int] = None
    generation_time_ms: Optional[int] = None


# Story 3.4: Feedback
class FeedbackCreateRequest(BaseModel):
    """Request per feedback thumbs up/down."""
    sessionId: str
    vote: Literal["up", "down"]
    comment: Optional[str] = None  # Story 5.5 Task 1: Campo opzionale per commento feedback


class FeedbackCreateResponse(BaseModel):
    """Response conferma feedback."""
    ok: bool


# Story 5.5: Chat Endpoint
class ChatRequest(BaseModel):
    """Request per RAG chat endpoint."""
    message: str
    session_id: str
    match_count: int = 8
    match_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Response per RAG chat endpoint."""
    answer: str
    session_id: str
    sources: Optional[list[dict]] = None


# Story 9.2: Session History Retrieval
class ConversationMessage(BaseModel):
    """Message in session history."""
    id: str
    role: Literal["user", "assistant"]
    content: str
    source_chunk_ids: Optional[list[str]] = None
    metadata: dict = Field(default_factory=dict)
    created_at: str


class SessionHistoryResponse(BaseModel):
    """Response per GET session history con pagination."""
    messages: list[ConversationMessage]
    total_count: int
    has_more: bool