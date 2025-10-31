"""
Unit tests for enhanced retrieval with cross-encoder re-ranking.

Story 7.2 AC1, AC4: Test lazy loading, re-ranking, fallback.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from api.knowledge_base.enhanced_retrieval import (
    EnhancedChunkRetriever,
    get_enhanced_retriever,
    _get_cross_encoder_model,
)
from api.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.cross_encoder_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    settings.cross_encoder_over_retrieve_factor = 3
    settings.cross_encoder_threshold_post_rerank = 0.6
    settings.enable_chunk_diversification = False
    settings.diversification_max_per_document = 2
    settings.diversification_preserve_top_n = 3
    return settings


@pytest.fixture
def mock_baseline_results():
    """Mock baseline search results."""
    return [
        {
            "id": "chunk1",
            "document_id": "doc1",
            "content": "Dolore lombare acuto trattamento",
            "similarity_score": 0.85,
        },
        {
            "id": "chunk2",
            "document_id": "doc1",
            "content": "Fisioterapia colonna vertebrale",
            "similarity_score": 0.78,
        },
        {
            "id": "chunk3",
            "document_id": "doc2",
            "content": "Esercizi core stability",
            "similarity_score": 0.72,
        },
        {
            "id": "chunk4",
            "document_id": "doc3",
            "content": "Mobilizzazione vertebrale",
            "similarity_score": 0.68,
        },
        {
            "id": "chunk5",
            "document_id": "doc2",
            "content": "Rinforzo muscolare paravertebrale",
            "similarity_score": 0.65,
        },
    ]


class TestEnhancedChunkRetriever:
    """Test EnhancedChunkRetriever class."""
    
    def test_init(self, mock_settings):
        """Test retriever initialization."""
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        assert retriever.settings == mock_settings
        assert retriever._baseline_search is None
    
    def test_lazy_loading_reranker_not_loaded_on_init(self, mock_settings):
        """Test che reranker NON sia loaded al init (lazy loading)."""
        with patch("api.knowledge_base.enhanced_retrieval._reranker_model", None):
            retriever = EnhancedChunkRetriever(settings=mock_settings)
            # Verifica che model NON sia loaded
            assert retriever._baseline_search is None
    
    @patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model")
    def test_lazy_loading_reranker_loaded_on_first_access(
        self, mock_get_model, mock_settings
    ):
        """Test che reranker sia loaded solo al primo accesso."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        _ = retriever.reranker  # Primo accesso
        
        mock_get_model.assert_called_once_with(
            mock_settings.cross_encoder_model_name
        )
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    @patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model")
    def test_retrieve_and_rerank_order(
        self, mock_get_model, mock_search, mock_settings, mock_baseline_results
    ):
        """Test che re-ranking ordini risultati correttamente."""
        # Mock baseline search
        mock_search.return_value = mock_baseline_results.copy()
        
        # Mock cross-encoder scores (inverti ordine per test)
        mock_model = MagicMock()
        mock_rerank_scores = np.array([0.5, 0.6, 0.95, 0.8, 0.7])  # chunk3 highest
        mock_model.predict.return_value = mock_rerank_scores
        mock_get_model.return_value = mock_model
        
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        results = retriever.retrieve_and_rerank(
            query="dolore lombare",
            match_count=3,
            match_threshold=0.6,
            diversify=False,
        )
        
        # Verifica over-retrieve (3x match_count)
        mock_search.assert_called_once()
        call_kwargs = mock_search.call_args[1]
        assert call_kwargs["match_count"] == 9  # 3 × 3
        assert call_kwargs["match_threshold"] == 0.4
        
        # Verifica batch prediction chiamata
        mock_model.predict.assert_called_once()
        
        # Verifica ordine risultati per rerank_score
        assert len(results) == 3
        assert results[0]["id"] == "chunk3"  # Highest rerank score (0.95)
        assert results[1]["id"] == "chunk4"  # Second (0.8)
        assert results[2]["id"] == "chunk5"  # Third (0.7)
        
        # Verifica scores arricchiti
        assert "rerank_score" in results[0]
        assert "bi_encoder_score" in results[0]
        assert "relevance_score" in results[0]
        assert results[0]["rerank_score"] == 0.95
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    def test_retrieve_and_rerank_threshold_filtering(
        self, mock_search, mock_settings, mock_baseline_results
    ):
        """Test che threshold filtering funzioni correttamente."""
        mock_search.return_value = mock_baseline_results.copy()
        
        with patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model") as mock_get_model:
            mock_model = MagicMock()
            # Scores sotto threshold (0.6)
            mock_rerank_scores = np.array([0.45, 0.55, 0.70, 0.65, 0.50])
            mock_model.predict.return_value = mock_rerank_scores
            mock_get_model.return_value = mock_model
            
            retriever = EnhancedChunkRetriever(settings=mock_settings)
            results = retriever.retrieve_and_rerank(
                query="test query",
                match_count=5,
                match_threshold=0.6,  # Threshold esplicito
                diversify=False,
            )
            
            # Solo 2 risultati sopra threshold (0.70, 0.65)
            assert len(results) == 2
            assert all(r.get("rerank_score", 0) >= 0.6 for r in results)
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    @patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model")
    def test_retrieve_and_rerank_fallback_on_error(
        self, mock_get_model, mock_search, mock_settings, mock_baseline_results
    ):
        """Test graceful degradation se re-ranking fallisce."""
        mock_search.return_value = mock_baseline_results.copy()
        
        # Mock cross-encoder che solleva eccezione
        mock_model = MagicMock()
        mock_model.predict.side_effect = Exception("Model inference failed")
        mock_get_model.return_value = mock_model
        
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        results = retriever.retrieve_and_rerank(
            query="test query",
            match_count=3,
            match_threshold=0.6,
            diversify=False,
        )
        
        # Fallback: ritorna baseline results (top 3)
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"  # Baseline order
        assert results[1]["id"] == "chunk2"
        assert results[2]["id"] == "chunk3"
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    def test_retrieve_and_rerank_no_initial_results(
        self, mock_search, mock_settings
    ):
        """Test che ritorna empty list se nessun risultato iniziale."""
        mock_search.return_value = []
        
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        results = retriever.retrieve_and_rerank(
            query="query senza risultati",
            match_count=5,
        )
        
        assert results == []
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    @patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model")
    def test_retrieve_and_rerank_circuit_breaker(
        self, mock_get_model, mock_search, mock_settings, mock_baseline_results
    ):
        """Test circuit breaker: skip re-ranking se initial retrieval lenta."""
        # Mock retrieval lenta (>1s delay simulato modificando il comportamento)
        def slow_search(*args, **kwargs):
            import time
            time.sleep(1.1)  # Simula latency >1000ms
            return mock_baseline_results.copy()
        
        mock_search.side_effect = slow_search
        
        retriever = EnhancedChunkRetriever(settings=mock_settings)
        results = retriever.retrieve_and_rerank(
            query="test query",
            match_count=3,
        )
        
        # Circuit breaker triggered: skip re-ranking, ritorna baseline top-k
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"  # Baseline order preserved
    
    @patch("api.knowledge_base.search.perform_semantic_search")
    @patch("api.knowledge_base.enhanced_retrieval._get_cross_encoder_model")
    def test_retrieve_and_rerank_with_diversification(
        self, mock_get_model, mock_search, mock_settings, mock_baseline_results
    ):
        """Test integration con diversification."""
        mock_settings.enable_chunk_diversification = True
        mock_search.return_value = mock_baseline_results.copy()
        
        mock_model = MagicMock()
        mock_rerank_scores = np.array([0.9, 0.85, 0.8, 0.75, 0.7])
        mock_model.predict.return_value = mock_rerank_scores
        mock_get_model.return_value = mock_model
        
        with patch("api.knowledge_base.diversification.diversify_chunks") as mock_diversify:
            mock_diversify.return_value = mock_baseline_results[:3]  # Simula diversification
            
            retriever = EnhancedChunkRetriever(settings=mock_settings)
            retriever.retrieve_and_rerank(
                query="test query",
                match_count=5,
                diversify=True,
            )
            
            # Verifica che diversify_chunks sia chiamato
            mock_diversify.assert_called_once()
            call_args = mock_diversify.call_args[1]
            assert call_args["max_per_doc"] == 2
            assert call_args["preserve_top_n"] == 3


def test_get_enhanced_retriever():
    """Test factory function."""
    with patch("api.knowledge_base.enhanced_retrieval.get_settings") as mock_get_settings:
        mock_settings = Mock(spec=Settings)
        mock_get_settings.return_value = mock_settings
        
        retriever = get_enhanced_retriever()
        
        assert isinstance(retriever, EnhancedChunkRetriever)
        assert retriever.settings == mock_settings


def test_get_cross_encoder_model_lazy_load():
    """Test lazy loading cross-encoder model."""
    with patch("api.knowledge_base.enhanced_retrieval._reranker_model", None):
        with patch("sentence_transformers.CrossEncoder") as mock_ce:
            mock_model = MagicMock()
            mock_ce.return_value = mock_model
            
            model = _get_cross_encoder_model("test-model")
            
            mock_ce.assert_called_once_with("test-model", max_length=512)
            assert model == mock_model


def test_get_cross_encoder_model_cached():
    """Test che model sia cached dopo primo load."""
    mock_cached_model = MagicMock()
    
    with patch("api.knowledge_base.enhanced_retrieval._reranker_model", mock_cached_model):
        model = _get_cross_encoder_model("test-model")
        
        # Ritorna cached model
        assert model == mock_cached_model

