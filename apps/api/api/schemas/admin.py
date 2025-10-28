"""
Admin schemas - Request/Response models per endpoint admin.

Story: 4.1
"""
from typing import Optional
from pydantic import BaseModel, Field


class DebugQueryRequest(BaseModel):
    """Request per debug query admin."""
    question: str = Field(..., description="Domanda di test per RAG debug")


class DebugChunkMetadata(BaseModel):
    """Metadati chunk per debug view."""
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    page_number: Optional[int] = None
    chunking_strategy: Optional[str] = None


class DebugChunkItem(BaseModel):
    """Chunk item con similarity score per debug."""
    chunk_id: Optional[str] = None
    content: Optional[str] = None
    similarity_score: Optional[float] = None
    metadata: Optional[DebugChunkMetadata] = None


class DebugQueryResponse(BaseModel):
    """Response completa debug query con metrics."""
    question: str
    answer: Optional[str] = None
    chunks: list[DebugChunkItem]
    retrieval_time_ms: int
    generation_time_ms: int


# Story 6.4 AC4 - Embedding Health Monitoring
class DocumentEmbeddingStatus(BaseModel):
    """Stato embedding per singolo documento."""
    document_id: str
    document_name: str
    total_chunks: int
    chunks_with_embeddings: int
    coverage_percent: float
    last_indexed_at: Optional[str] = None  # ISO-8601 timestamp
    status: Optional[str] = None  # "COMPLETE" | "PARTIAL" | "NONE"


class EmbeddingHealthSummary(BaseModel):
    """Summary aggregato coverage embeddings."""
    total_documents: int
    total_chunks: int
    chunks_with_embeddings: int
    chunks_without_embeddings: int
    embedding_coverage_percent: float
    last_indexed_at: Optional[str] = None  # ISO-8601 timestamp del doc più recente
    # Story 6.4 NFR - Performance Metrics (QA must-fix TEST-002)
    avg_indexing_time_ms: Optional[float] = None  # Tempo medio indicizzazione per chunk
    avg_retrieval_time_ms: Optional[float] = None  # Tempo medio recupero (p95 target <2s)


class EmbeddingHealthResponse(BaseModel):
    """Response endpoint embedding health (AC4)."""
    summary: EmbeddingHealthSummary
    by_document: list[DocumentEmbeddingStatus]
    warnings: list[str] = Field(default_factory=list)