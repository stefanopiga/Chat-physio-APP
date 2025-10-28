"""
Unit tests for chunk diversification.

Story 7.2 AC3: Test anti-ridondanza algorithm.
"""
import pytest

from api.knowledge_base.diversification import (
    diversify_chunks,
    get_document_distribution,
    calculate_diversity_score,
)


@pytest.fixture
def sample_chunks():
    """Sample chunks for testing."""
    return [
        {"id": "chunk1", "document_id": "doc1", "content": "Content 1", "rerank_score": 0.9},
        {"id": "chunk2", "document_id": "doc1", "content": "Content 2", "rerank_score": 0.85},
        {"id": "chunk3", "document_id": "doc2", "content": "Content 3", "rerank_score": 0.8},
        {"id": "chunk4", "document_id": "doc1", "content": "Content 4", "rerank_score": 0.75},
        {"id": "chunk5", "document_id": "doc3", "content": "Content 5", "rerank_score": 0.7},
        {"id": "chunk6", "document_id": "doc2", "content": "Content 6", "rerank_score": 0.65},
        {"id": "chunk7", "document_id": "doc1", "content": "Content 7", "rerank_score": 0.6},
    ]


class TestDiversifyChunks:
    """Test diversify_chunks function."""
    
    def test_diversify_enforces_max_per_document(self, sample_chunks):
        """Test che max_per_document limit sia enforced."""
        diversified = diversify_chunks(
            chunks=sample_chunks,
            max_per_doc=2,
            preserve_top_n=3,
        )
        
        # Conta chunk per documento
        doc_counts = {}
        for chunk in diversified:
            doc_id = chunk.get("document_id")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        
        # Verifica max 2 chunk per documento
        for doc_id, count in doc_counts.items():
            assert count <= 2, f"Documento {doc_id} ha {count} chunk (max 2)"
    
    def test_diversify_preserves_top_n(self, sample_chunks):
        """Test che top-N chunk siano sempre preservati."""
        diversified = diversify_chunks(
            chunks=sample_chunks,
            max_per_doc=2,
            preserve_top_n=3,
        )
        
        # Top-3 chunk devono essere presenti (anche se da stesso documento)
        top_3_ids = [c["id"] for c in sample_chunks[:3]]
        diversified_ids = [c["id"] for c in diversified]
        
        for chunk_id in top_3_ids:
            assert chunk_id in diversified_ids, f"Top-3 chunk {chunk_id} deve essere preservato"
    
    def test_diversify_maintains_relevance_order(self, sample_chunks):
        """Test che relevance order sia mantenuto."""
        diversified = diversify_chunks(
            chunks=sample_chunks,
            max_per_doc=2,
            preserve_top_n=3,
        )
        
        # Verifica che rerank_scores siano in ordine decrescente
        scores = [c.get("rerank_score", 0) for c in diversified]
        assert scores == sorted(scores, reverse=True), "Scores devono essere ordinati (descending)"
    
    def test_diversify_empty_input(self):
        """Test che empty input ritorni empty list."""
        diversified = diversify_chunks(chunks=[], max_per_doc=2)
        assert diversified == []
    
    def test_diversify_single_chunk(self):
        """Test con singolo chunk."""
        single_chunk = [{"id": "chunk1", "document_id": "doc1", "content": "Test"}]
        diversified = diversify_chunks(chunks=single_chunk, max_per_doc=2)
        
        assert len(diversified) == 1
        assert diversified[0]["id"] == "chunk1"
    
    def test_diversify_no_document_id(self):
        """Test che chunk senza document_id siano inclusi sempre."""
        chunks_no_doc_id = [
            {"id": "chunk1", "content": "Content 1", "rerank_score": 0.9},
            {"id": "chunk2", "content": "Content 2", "rerank_score": 0.8},
        ]
        
        diversified = diversify_chunks(chunks=chunks_no_doc_id, max_per_doc=1)
        
        # Tutti chunk senza doc_id devono essere inclusi
        assert len(diversified) == 2
    
    def test_diversify_invalid_max_per_doc(self, sample_chunks):
        """Test che max_per_doc <= 0 ritorni original chunks."""
        diversified = diversify_chunks(chunks=sample_chunks, max_per_doc=0)
        assert diversified == sample_chunks
    
    def test_diversify_max_per_doc_1(self, sample_chunks):
        """Test con max_per_doc=1 (massima diversità)."""
        diversified = diversify_chunks(
            chunks=sample_chunks,
            max_per_doc=1,
            preserve_top_n=0,  # No preservation
        )
        
        # Ogni documento al massimo 1 chunk
        doc_counts = {}
        for chunk in diversified:
            doc_id = chunk.get("document_id")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        
        for doc_id, count in doc_counts.items():
            assert count == 1, f"Documento {doc_id} dovrebbe avere 1 chunk"
    
    def test_diversify_preserve_top_n_exceeds_max_per_doc(self):
        """Test che top-N preservation abbia priorità su max_per_doc."""
        chunks = [
            {"id": "chunk1", "document_id": "doc1", "rerank_score": 0.9},
            {"id": "chunk2", "document_id": "doc1", "rerank_score": 0.85},
            {"id": "chunk3", "document_id": "doc1", "rerank_score": 0.8},
            {"id": "chunk4", "document_id": "doc2", "rerank_score": 0.75},
        ]
        
        diversified = diversify_chunks(
            chunks=chunks,
            max_per_doc=1,
            preserve_top_n=3,  # Top-3 tutti da doc1
        )
        
        # Top-3 chunk (tutti doc1) devono essere preservati
        assert len(diversified) >= 3
        assert diversified[0]["id"] == "chunk1"
        assert diversified[1]["id"] == "chunk2"
        assert diversified[2]["id"] == "chunk3"


class TestGetDocumentDistribution:
    """Test get_document_distribution function."""
    
    def test_get_document_distribution(self, sample_chunks):
        """Test document distribution calculation."""
        distribution = get_document_distribution(sample_chunks)
        
        assert distribution["doc1"] == 4
        assert distribution["doc2"] == 2
        assert distribution["doc3"] == 1
    
    def test_get_document_distribution_empty(self):
        """Test con empty chunks."""
        distribution = get_document_distribution([])
        assert distribution == {}
    
    def test_get_document_distribution_no_doc_id(self):
        """Test con chunk senza document_id."""
        chunks = [
            {"id": "chunk1", "content": "Test 1"},
            {"id": "chunk2", "document_id": "doc1", "content": "Test 2"},
        ]
        
        distribution = get_document_distribution(chunks)
        assert distribution.get("doc1") == 1


class TestCalculateDiversityScore:
    """Test calculate_diversity_score function."""
    
    def test_diversity_score_perfect(self):
        """Test perfect diversity (ogni chunk da documento diverso)."""
        chunks = [
            {"id": "chunk1", "document_id": "doc1"},
            {"id": "chunk2", "document_id": "doc2"},
            {"id": "chunk3", "document_id": "doc3"},
        ]
        
        score = calculate_diversity_score(chunks)
        assert score == 1.0
    
    def test_diversity_score_worst(self):
        """Test worst diversity (tutti chunk da stesso documento)."""
        chunks = [
            {"id": "chunk1", "document_id": "doc1"},
            {"id": "chunk2", "document_id": "doc1"},
            {"id": "chunk3", "document_id": "doc1"},
        ]
        
        score = calculate_diversity_score(chunks)
        assert score == pytest.approx(0.333, abs=0.01)
    
    def test_diversity_score_mixed(self, sample_chunks):
        """Test diversity score con mix documenti."""
        # doc1: 4 chunk, doc2: 2 chunk, doc3: 1 chunk
        # unique: 3, total: 7
        score = calculate_diversity_score(sample_chunks)
        expected = 3 / 7  # 0.428
        
        assert score == pytest.approx(expected, abs=0.01)
    
    def test_diversity_score_empty(self):
        """Test con empty chunks."""
        score = calculate_diversity_score([])
        assert score == 0.0
    
    def test_diversity_score_no_doc_id(self):
        """Test con chunk senza document_id."""
        chunks = [
            {"id": "chunk1", "content": "Test 1"},
            {"id": "chunk2", "content": "Test 2"},
        ]
        
        score = calculate_diversity_score(chunks)
        # Nessun document_id → assume diversity 1.0 (non penalizziamo)
        assert score == 1.0
    
    def test_diversity_score_improvement(self):
        """Test che diversification migliori diversity score."""
        chunks = [
            {"id": "chunk1", "document_id": "doc1", "rerank_score": 0.9},
            {"id": "chunk2", "document_id": "doc1", "rerank_score": 0.85},
            {"id": "chunk3", "document_id": "doc1", "rerank_score": 0.8},
            {"id": "chunk4", "document_id": "doc2", "rerank_score": 0.75},
            {"id": "chunk5", "document_id": "doc3", "rerank_score": 0.7},
        ]
        
        score_before = calculate_diversity_score(chunks)
        
        diversified = diversify_chunks(chunks, max_per_doc=2, preserve_top_n=3)
        score_after = calculate_diversity_score(diversified)
        
        # Diversity score dovrebbe migliorare
        assert score_after >= score_before

