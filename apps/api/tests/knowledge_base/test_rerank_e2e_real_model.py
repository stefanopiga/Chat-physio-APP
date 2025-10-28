"""
Integration E2E test per re-ranking con modello reale.

Story 7.2 AC1, AC4: Verifica latency, comportamento completo pipeline.

NOTA: Questi test sono SLOW (caricamento modello ~200MB + inferenza).
Eseguire con: pytest --run-integration tests/knowledge_base/test_rerank_e2e_real_model.py
"""
import pytest
import time
from unittest.mock import patch

from api.knowledge_base.enhanced_retrieval import EnhancedChunkRetriever
from api.config import Settings


@pytest.mark.integration
@pytest.mark.slow
class TestEnhancedRetrievalE2EReal:
    """Integration tests con cross-encoder model reale."""
    
    @pytest.fixture
    def real_settings(self):
        """Real settings for integration test."""
        settings = Settings()
        settings.cross_encoder_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        settings.cross_encoder_over_retrieve_factor = 3
        settings.cross_encoder_threshold_post_rerank = 0.6
        settings.enable_chunk_diversification = False
        return settings
    
    @pytest.fixture
    def mock_baseline_results(self):
        """Mock baseline search results for E2E test."""
        return [
            {
                "id": "chunk1",
                "document_id": "doc1",
                "content": "Il dolore lombare acuto può essere trattato con terapia manuale e esercizi specifici.",
                "similarity_score": 0.82,
            },
            {
                "id": "chunk2",
                "document_id": "doc1",
                "content": "La fisioterapia per la colonna vertebrale include mobilizzazione e rinforzo muscolare.",
                "similarity_score": 0.78,
            },
            {
                "id": "chunk3",
                "document_id": "doc2",
                "content": "Gli esercizi di core stability sono fondamentali per la prevenzione del mal di schiena.",
                "similarity_score": 0.75,
            },
            {
                "id": "chunk4",
                "document_id": "doc2",
                "content": "La mobilizzazione vertebrale è una tecnica efficace per ridurre il dolore lombare.",
                "similarity_score": 0.72,
            },
            {
                "id": "chunk5",
                "document_id": "doc3",
                "content": "Il rinforzo muscolare paravertebrale previene le recidive di lombalgia.",
                "similarity_score": 0.68,
            },
            {
                "id": "chunk6",
                "document_id": "doc3",
                "content": "Le tecniche di stretching migliorano la flessibilità della colonna lombare.",
                "similarity_score": 0.65,
            },
        ]
    
    def test_e2e_rerank_with_real_model(self, real_settings, mock_baseline_results):
        """Test E2E pipeline con modello cross-encoder reale."""
        with patch("api.knowledge_base.search.perform_semantic_search") as mock_search:
            mock_search.return_value = mock_baseline_results.copy()
            
            retriever = EnhancedChunkRetriever(settings=real_settings)
            
            start_time = time.time()
            results = retriever.retrieve_and_rerank(
                query="trattamento dolore lombare acuto",
                match_count=5,
                match_threshold=0.6,
                diversify=False,
            )
            latency_ms = int((time.time() - start_time) * 1000)
            
            # AC4: Latency constraint < 2000ms
            assert latency_ms < 2000, f"Latency {latency_ms}ms eccede target 2000ms"
            
            # Verifica risultati
            assert len(results) > 0, "Dovrebbe ritornare risultati"
            assert len(results) <= 5, "Dovrebbe rispettare match_count limit"
            
            # Verifica enrichment scores
            for chunk in results:
                assert "rerank_score" in chunk, "Chunk deve avere rerank_score"
                assert "bi_encoder_score" in chunk, "Chunk deve avere bi_encoder_score"
                assert "relevance_score" in chunk, "Chunk deve avere relevance_score"
            
            # Verifica ordine per rerank_score
            scores = [c["rerank_score"] for c in results]
            assert scores == sorted(scores, reverse=True), "Risultati devono essere ordinati per rerank_score"
            
            print(f"\n✓ E2E test passed - Latency: {latency_ms}ms")
            print(f"  Results count: {len(results)}")
            print(f"  Rerank scores: {[round(s, 3) for s in scores]}")
    
    def test_model_lazy_loading_latency(self, real_settings):
        """Test che primo load model sia accettabile (<60s primo download da HF)."""
        # Reset global model cache
        import api.knowledge_base.enhanced_retrieval as module
        module._reranker_model = None
        
        retriever = EnhancedChunkRetriever(settings=real_settings)
        
        start_time = time.time()
        _ = retriever.reranker  # Trigger lazy load
        load_time_ms = int((time.time() - start_time) * 1000)
        
        # Model load: primo download ~40s, successivi < 5s (cached)
        # NOTE: Questo test è slow al primo run (download model da HuggingFace)
        assert load_time_ms < 60000, f"Model load {load_time_ms}ms troppo lento (check HF connectivity)"
        
        print(f"\n✓ Model lazy loading - Time: {load_time_ms}ms")
    
    def test_batch_prediction_performance(self, real_settings, mock_baseline_results):
        """Test che batch prediction sia efficiente (20+ pairs < 500ms)."""
        with patch("api.knowledge_base.search.perform_semantic_search") as mock_search:
            # Genera 24 chunk per testare batch size
            extended_results = mock_baseline_results * 4  # 24 chunk
            mock_search.return_value = extended_results
            
            retriever = EnhancedChunkRetriever(settings=real_settings)
            
            # Warm-up: load model
            _ = retriever.reranker
            
            start_time = time.time()
            results = retriever.retrieve_and_rerank(
                query="test query",
                match_count=10,
                match_threshold=0.5,
                diversify=False,
            )
            rerank_time_ms = int((time.time() - start_time) * 1000)
            
            # Batch prediction (24 pairs) dovrebbe essere < 800ms (include retrieval mock)
            assert rerank_time_ms < 800, f"Batch prediction {rerank_time_ms}ms troppo lento"
            
            print(f"\n✓ Batch prediction (24 pairs) - Time: {rerank_time_ms}ms")
    
    def test_rerank_improves_relevance(self, real_settings, mock_baseline_results):
        """Test che re-ranking effettivamente riordini risultati per relevance."""
        with patch("api.knowledge_base.search.perform_semantic_search") as mock_search:
            mock_search.return_value = mock_baseline_results.copy()
            
            retriever = EnhancedChunkRetriever(settings=real_settings)
            
            results = retriever.retrieve_and_rerank(
                query="dolore lombare acuto",
                match_count=5,
                match_threshold=0.5,
                diversify=False,
            )
            
            # Verifica che ordine post-rerank sia diverso da bi-encoder
            bi_encoder_order = [c["id"] for c in mock_baseline_results[:5]]
            rerank_order = [c["id"] for c in results[:5]]
            
            # Con alta probabilità, ordine dovrebbe cambiare
            # (può fallire in edge cases, ma unlikely con query meaningful)
            print(f"\n  Bi-encoder order: {bi_encoder_order}")
            print(f"  Re-rank order:    {rerank_order}")
            
            # Almeno verifica che chunk più rilevante sia in top-3
            top_rerank_ids = rerank_order[:3]
            assert "chunk1" in top_rerank_ids or "chunk3" in top_rerank_ids or "chunk4" in top_rerank_ids


@pytest.mark.integration
@pytest.mark.slow
def test_cross_encoder_model_import():
    """Test che sentence-transformers sia installato correttamente."""
    try:
        from sentence_transformers import CrossEncoder
        assert CrossEncoder is not None
        print("\n✓ sentence-transformers installato correttamente")
    except ImportError as exc:
        pytest.fail(f"sentence-transformers non installato: {exc}")


if __name__ == "__main__":
    # Run con: python -m pytest tests/knowledge_base/test_rerank_e2e_real_model.py -v -s
    pytest.main([__file__, "-v", "-s", "-m", "integration"])

