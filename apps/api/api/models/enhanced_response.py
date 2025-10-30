"""
Enhanced Academic Response Models (Story 7.1).

Pydantic models per risposte strutturate in componenti pedagogici
con citazioni arricchite e metadata di confidenza.

Features:
- 7 campi semantici validati (introduzione, concetti, spiegazione, etc.)
- CitationMetadata arricchita con document_name, page, excerpt
- ResponseMetadata per analytics e monitoring
- Validators per constraints (min/max lengths, ranges)
"""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CitationMetadata(BaseModel):
    """
    Metadata arricchita per singola citazione.
    
    Story 7.1 AC5: Include document_name, page_number, excerpt
    per supportare popover ricchi nel frontend.
    """
    chunk_id: str = Field(
        ...,
        description="ID univoco del chunk citato",
        min_length=1,
    )
    document_id: str = Field(
        ...,
        description="ID del documento sorgente",
        min_length=1,
    )
    document_name: Optional[str] = Field(
        default=None,
        description="Nome leggibile del documento (es. 'Spondilolistesi.docx')",
        max_length=255,
    )
    page_number: Optional[int] = Field(
        default=None,
        description="Numero pagina nel documento originale",
        ge=1,
    )
    relevance_score: Optional[float] = Field(
        default=None,
        description="Similarity score dalla semantic search",
        ge=0.0,
        le=1.0,
    )
    excerpt: Optional[str] = Field(
        default=None,
        description="Estratto testuale del chunk citato (max 1000 char)",
        max_length=1000,
    )
    content_type: Optional[Literal["text", "table", "figure"]] = Field(
        default="text",
        description="Tipo di contenuto citato",
    )

    @field_validator("document_name")
    @classmethod
    def validate_document_name(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize document name: remove empty strings."""
        if v is not None and not v.strip():
            return None
        return v

    @field_validator("excerpt")
    @classmethod
    def validate_excerpt(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize excerpt: remove empty strings."""
        if v is not None and not v.strip():
            return None
        return v


class EnhancedAcademicResponse(BaseModel):
    """
    Risposta strutturata accademico-pedagogica (Story 7.1 AC2).
    
    Componenti semantici:
    - introduzione: Contestualizzazione iniziale (20-500 char)
    - concetti_chiave: 2-5 punti essenziali
    - spiegazione_dettagliata: Sviluppo logico progressivo (min 100 char)
    - note_cliniche: Applicazioni pratiche (opzionale, max 1000 char)
    - limitazioni_contesto: Disclaimer su scope risposta (opzionale, max 500 char)
    - citazioni: List CitationMetadata (min 1)
    - confidenza_risposta: alta/media/bassa
    """
    introduzione: str = Field(
        ...,
        description="Contestualizzazione breve dell'argomento (1-3 frasi)",
        min_length=20,
        max_length=500,
    )
    concetti_chiave: List[str] = Field(
        ...,
        description="Lista 2-5 concetti essenziali esplicitati",
        min_length=2,
        max_length=5,
    )
    spiegazione_dettagliata: str = Field(
        ...,
        description="Sviluppo logico progressivo della risposta",
        min_length=100,
    )
    note_cliniche: Optional[str] = Field(
        default=None,
        description="Applicazioni pratiche, implicazioni cliniche (opzionale)",
        max_length=1000,
    )
    limitazioni_contesto: Optional[str] = Field(
        default=None,
        description="Disclaimer su scope/limiti della risposta fornita",
        max_length=500,
    )
    citazioni: List[CitationMetadata] = Field(
        ...,
        description="Citazioni con metadata arricchiti (min 1)",
        min_length=1,
    )
    confidenza_risposta: Literal["alta", "media", "bassa"] = Field(
        ...,
        description="Livello confidenza rispetto al contesto disponibile",
    )

    @field_validator("concetti_chiave")
    @classmethod
    def validate_concetti_chiave(cls, v: List[str]) -> List[str]:
        """
        Valida che concetti_chiave siano non-vuoti e non duplicati.
        """
        if not v:
            raise ValueError("concetti_chiave non può essere lista vuota")
        
        # Remove empty strings
        cleaned = [item.strip() for item in v if item and item.strip()]
        if len(cleaned) < 2:
            raise ValueError("concetti_chiave deve contenere almeno 2 concetti non vuoti")
        if len(cleaned) > 5:
            raise ValueError("concetti_chiave deve contenere massimo 5 concetti")
        
        # Check duplicates (case-insensitive)
        lower_items = [item.lower() for item in cleaned]
        if len(lower_items) != len(set(lower_items)):
            raise ValueError("concetti_chiave non può contenere duplicati")
        
        return cleaned

    @field_validator("spiegazione_dettagliata")
    @classmethod
    def validate_spiegazione_dettagliata(cls, v: str) -> str:
        """Valida lunghezza minima spiegazione dettagliata."""
        if not v or len(v.strip()) < 100:
            raise ValueError("spiegazione_dettagliata deve contenere almeno 100 caratteri")
        return v.strip()

    @field_validator("note_cliniche", "limitazioni_contesto")
    @classmethod
    def validate_optional_fields(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize optional fields: convert empty strings to None."""
        if v is not None and not v.strip():
            return None
        return v


class ResponseMetadata(BaseModel):
    """
    Metadata per analytics e monitoring (Story 7.1 AC7).
    
    Traccia:
    - Metriche performance (latency, token counts)
    - Contesto conversazionale usato
    - Feature flags attivi durante generazione
    """
    response_id: str = Field(
        ...,
        description="ID univoco risposta generata",
    )
    session_id: str = Field(
        ...,
        description="ID sessione conversazionale",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp generazione risposta (UTC)",
    )
    
    # Performance metrics
    retrieval_time_ms: int = Field(
        ...,
        description="Latenza retrieval chunk (ms)",
        ge=0,
    )
    generation_time_ms: int = Field(
        ...,
        description="Latenza generazione LLM (ms)",
        ge=0,
    )
    total_time_ms: int = Field(
        ...,
        description="Latenza totale end-to-end (ms)",
        ge=0,
    )
    
    # Context metrics
    chunks_retrieved: int = Field(
        ...,
        description="Numero chunk recuperati da semantic search",
        ge=0,
    )
    chunks_cited: int = Field(
        ...,
        description="Numero chunk effettivamente citati in risposta",
        ge=0,
    )
    conversation_turns_context: int = Field(
        default=0,
        description="Numero turni conversazionali inclusi nel context window",
        ge=0,
    )
    conversation_tokens_context: int = Field(
        default=0,
        description="Token totali usati per conversational context",
        ge=0,
    )
    
    # Feature flags snapshot
    used_enhanced_model: bool = Field(
        default=False,
        description="Flag: enhanced response model attivo",
    )
    used_conversational_memory: bool = Field(
        default=False,
        description="Flag: conversational memory attiva",
    )
    used_academic_prompt: bool = Field(
        default=False,
        description="Flag: academic prompt attivo",
    )
    
    # User interaction
    user_id: Optional[str] = Field(
        default=None,
        description="User ID se disponibile da JWT",
    )
    user_query: str = Field(
        ...,
        description="Query originale utente",
        max_length=2000,
    )

