"""
Knowledge Base schemas - Request/Response models per knowledge base operations.

Story: 2.2, 2.4, 2.5, 4.4
"""
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from ..ingestion.models import ClassificazioneOutput


# Story 2.2: Classificazione
class ClassifyRequest(BaseModel):
    """Request per classificazione documento."""
    testo: str = Field(..., description="Testo documento da classificare")


class ClassifyResponse(ClassificazioneOutput):
    """Response classificazione (alias ClassificazioneOutput)."""
    pass


# Story 2.4: Semantic Search
class SearchRequest(BaseModel):
    """Request per ricerca semantica knowledge base."""
    query: str
    match_count: int = Field(default=8, ge=1, le=50)
    match_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """Response ricerca semantica con risultati."""
    results: list[dict]


# Story 2.4 + 2.5: Sync Jobs
class StartSyncJobRequest(BaseModel):
    """Request per avvio sync job knowledge base."""
    document_text: str
    classification: Optional[ClassificazioneOutput] = None
    metadata: Optional[Dict[str, Any]] = None


class StartSyncJobResponse(BaseModel):
    """Response avvio sync job con job_id e timing metrics."""
    job_id: str
    inserted: Optional[int] = None
    document_id: Optional[str] = None
    timing: Optional[Dict[str, int]] = None  # Story 2.5: timing metrics


class SyncJobStatusResponse(BaseModel):
    """Response status sync job."""
    job_id: str
    status: str
    inserted: Optional[int] = None
    error: Optional[str] = None
    document_id: Optional[str] = None


# Story 4.4: Document Explorer
class DocumentSummary(BaseModel):
    """Summary documento con metadata aggregati."""
    document_id: str
    document_name: str
    upload_date: str  # ISO datetime
    chunk_count: int
    primary_chunking_strategy: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response lista documenti."""
    documents: list[DocumentSummary]
    total_count: int


class ChunkDetail(BaseModel):
    """Dettaglio chunk per document explorer."""
    chunk_id: str
    content: str
    chunk_size: int
    chunk_index: Optional[int] = None
    chunking_strategy: Optional[str] = None
    page_number: Optional[int] = None
    embedding_status: Literal["indexed", "pending"]
    created_at: str


class DocumentChunksResponse(BaseModel):
    """Response chunks per documento specifico (Story 4.4, 5.4 Task 2.1)."""
    document_id: str
    document_name: str
    chunks: list[ChunkDetail]
    total_chunks: int
