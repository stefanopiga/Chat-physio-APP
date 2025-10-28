"""
Test suite per Enhanced Academic Response Models (Story 7.1).

Coverage:
- CitationMetadata validation (fields, ranges, sanitization)
- EnhancedAcademicResponse validation (7 campi, constraints)
- ResponseMetadata completeness
- Validator logic (concetti_chiave, spiegazione_dettagliata, etc.)
"""
import pytest
from datetime import datetime, timezone

from api.models.enhanced_response import (
    CitationMetadata,
    EnhancedAcademicResponse,
    ResponseMetadata,
)


class TestCitationMetadata:
    """Test CitationMetadata model validation."""
    
    def test_citation_metadata_valid_minimal(self):
        """Test valid minimal citation with required fields only."""
        citation = CitationMetadata(
            chunk_id="chunk_123",
            document_id="doc_456",
        )
        assert citation.chunk_id == "chunk_123"
        assert citation.document_id == "doc_456"
        assert citation.document_name is None
        assert citation.page_number is None
        assert citation.relevance_score is None
        assert citation.excerpt is None
        assert citation.content_type == "text"  # default
    
    def test_citation_metadata_valid_complete(self):
        """Test valid complete citation with all fields."""
        citation = CitationMetadata(
            chunk_id="chunk_123",
            document_id="doc_456",
            document_name="Spondilolistesi.docx",
            page_number=5,
            relevance_score=0.87,
            excerpt="La spondilolistesi è una condizione...",
            content_type="text",
        )
        assert citation.document_name == "Spondilolistesi.docx"
        assert citation.page_number == 5
        assert citation.relevance_score == 0.87
        assert citation.content_type == "text"
    
    def test_citation_metadata_sanitize_empty_document_name(self):
        """Test empty document_name sanitized to None."""
        citation = CitationMetadata(
            chunk_id="chunk_123",
            document_id="doc_456",
            document_name="   ",  # empty string
        )
        assert citation.document_name is None
    
    def test_citation_metadata_sanitize_empty_excerpt(self):
        """Test empty excerpt sanitized to None."""
        citation = CitationMetadata(
            chunk_id="chunk_123",
            document_id="doc_456",
            excerpt="",
        )
        assert citation.excerpt is None
    
    def test_citation_metadata_invalid_page_number(self):
        """Test page_number validation (ge=1)."""
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            CitationMetadata(
                chunk_id="chunk_123",
                document_id="doc_456",
                page_number=0,
            )
    
    def test_citation_metadata_invalid_relevance_score(self):
        """Test relevance_score range validation (0.0-1.0)."""
        with pytest.raises(ValueError):
            CitationMetadata(
                chunk_id="chunk_123",
                document_id="doc_456",
                relevance_score=1.5,  # > 1.0
            )


class TestEnhancedAcademicResponse:
    """Test EnhancedAcademicResponse model validation."""
    
    @pytest.fixture
    def valid_citation(self):
        """Fixture: valid citation."""
        return CitationMetadata(
            chunk_id="chunk_123",
            document_id="doc_456",
            document_name="Test.docx",
            relevance_score=0.85,
        )
    
    def test_enhanced_response_valid_minimal(self, valid_citation):
        """Test valid minimal response with required fields only."""
        response = EnhancedAcademicResponse(
            introduzione="La spondilolistesi è una condizione vertebrale.",
            concetti_chiave=["Slittamento vertebrale", "Classificazione Meyerding"],
            spiegazione_dettagliata=(
                "La spondilolistesi consiste nello scivolamento anteriore "
                "di una vertebra rispetto a quella sottostante. "
                "Si classifica secondo Meyerding in gradi I-IV."
            ),
            citazioni=[valid_citation],
            confidenza_risposta="alta",
        )
        assert response.introduzione == "La spondilolistesi è una condizione vertebrale."
        assert len(response.concetti_chiave) == 2
        assert response.note_cliniche is None
        assert response.limitazioni_contesto is None
        assert len(response.citazioni) == 1
    
    def test_enhanced_response_valid_complete(self, valid_citation):
        """Test valid complete response with all fields."""
        response = EnhancedAcademicResponse(
            introduzione="La spondilolistesi è una condizione vertebrale.",
            concetti_chiave=[
                "Slittamento vertebrale",
                "Classificazione Meyerding",
                "Indicazioni chirurgiche"
            ],
            spiegazione_dettagliata=(
                "La spondilolistesi consiste nello scivolamento anteriore "
                "di una vertebra rispetto a quella sottostante. "
                "Si classifica secondo Meyerding in gradi I-IV."
            ),
            note_cliniche="Considerare valutazione neurochirurgica per gradi III-IV.",
            limitazioni_contesto="Risposta basata su materiale didattico generale.",
            citazioni=[valid_citation],
            confidenza_risposta="media",
        )
        assert response.note_cliniche is not None
        assert response.limitazioni_contesto is not None
        assert response.confidenza_risposta == "media"
    
    def test_enhanced_response_introduzione_too_short(self, valid_citation):
        """Test introduzione min_length validation (20 char)."""
        with pytest.raises(ValueError, match="at least 20 characters"):
            EnhancedAcademicResponse(
                introduzione="Troppo breve",  # < 20 char
                concetti_chiave=["A", "B"],
                spiegazione_dettagliata="x" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_introduzione_too_long(self, valid_citation):
        """Test introduzione max_length validation (500 char)."""
        with pytest.raises(ValueError, match="at most 500 characters"):
            EnhancedAcademicResponse(
                introduzione="x" * 501,  # > 500 char
                concetti_chiave=["A", "B"],
                spiegazione_dettagliata="y" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_concetti_chiave_too_few(self, valid_citation):
        """Test concetti_chiave min_items validation (2)."""
        with pytest.raises(ValueError, match="at least 2 items"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["Solo uno"],  # < 2
                spiegazione_dettagliata="x" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_concetti_chiave_too_many(self, valid_citation):
        """Test concetti_chiave max_items validation (5)."""
        with pytest.raises(ValueError, match="at most 5 items"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["A", "B", "C", "D", "E", "F"],  # > 5
                spiegazione_dettagliata="x" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_concetti_chiave_duplicates(self, valid_citation):
        """Test concetti_chiave no duplicates validation."""
        with pytest.raises(ValueError, match="non può contenere duplicati"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["Slittamento", "slittamento", "Altro"],  # duplicate
                spiegazione_dettagliata="x" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_concetti_chiave_empty_strings(self, valid_citation):
        """Test concetti_chiave removes empty strings."""
        with pytest.raises(ValueError, match="almeno 2 concetti"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["Valido", "", "  "],  # empty strings removed
                spiegazione_dettagliata="x" * 100,
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_spiegazione_too_short(self, valid_citation):
        """Test spiegazione_dettagliata min_length validation (100 char)."""
        with pytest.raises(ValueError, match="at least 100 characters"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["A", "B"],
                spiegazione_dettagliata="Troppo breve",  # < 100 char
                citazioni=[valid_citation],
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_citazioni_empty_list(self):
        """Test citazioni min_items validation (1)."""
        with pytest.raises(ValueError, match="at least 1 item"):
            EnhancedAcademicResponse(
                introduzione="La spondilolistesi è una condizione vertebrale.",
                concetti_chiave=["A", "B"],
                spiegazione_dettagliata="x" * 100,
                citazioni=[],  # empty
                confidenza_risposta="alta",
            )
    
    def test_enhanced_response_optional_fields_sanitization(self, valid_citation):
        """Test optional fields sanitized (empty strings → None)."""
        response = EnhancedAcademicResponse(
            introduzione="La spondilolistesi è una condizione vertebrale.",
            concetti_chiave=["A", "B"],
            spiegazione_dettagliata="x" * 100,
            note_cliniche="   ",  # empty string
            limitazioni_contesto="",
            citazioni=[valid_citation],
            confidenza_risposta="alta",
        )
        assert response.note_cliniche is None
        assert response.limitazioni_contesto is None


class TestResponseMetadata:
    """Test ResponseMetadata model completeness."""
    
    def test_response_metadata_valid(self):
        """Test valid metadata with all required fields."""
        metadata = ResponseMetadata(
            response_id="resp_123",
            session_id="sess_456",
            retrieval_time_ms=150,
            generation_time_ms=800,
            total_time_ms=950,
            chunks_retrieved=5,
            chunks_cited=3,
            conversation_turns_context=2,
            conversation_tokens_context=450,
            used_enhanced_model=True,
            used_conversational_memory=True,
            used_academic_prompt=True,
            user_id="user_789",
            user_query="Cos'è la spondilolistesi?",
        )
        assert metadata.response_id == "resp_123"
        assert metadata.chunks_retrieved == 5
        assert metadata.chunks_cited == 3
        assert metadata.conversation_turns_context == 2
        assert metadata.used_enhanced_model is True
    
    def test_response_metadata_timestamp_default(self):
        """Test timestamp defaults to current UTC."""
        metadata = ResponseMetadata(
            response_id="resp_123",
            session_id="sess_456",
            retrieval_time_ms=150,
            generation_time_ms=800,
            total_time_ms=950,
            chunks_retrieved=5,
            chunks_cited=3,
            user_query="Test query",
        )
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.timestamp.tzinfo == timezone.utc
    
    def test_response_metadata_negative_latency(self):
        """Test latency metrics validation (ge=0)."""
        with pytest.raises(ValueError):
            ResponseMetadata(
                response_id="resp_123",
                session_id="sess_456",
                retrieval_time_ms=-10,  # invalid
                generation_time_ms=800,
                total_time_ms=790,
                chunks_retrieved=5,
                chunks_cited=3,
                user_query="Test",
            )

