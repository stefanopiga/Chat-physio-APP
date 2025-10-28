"""
Enhanced chunk retrieval with cross-encoder re-ranking.

Story 7.2 AC1, AC4: Hybrid retrieval pipeline con over-retrieve, re-rank, diversify.

Pattern:
1. Over-retrieve: 3x target count, lower threshold (0.4)
2. Re-rank: cross-encoder batch prediction (20+ pairs)
3. Diversify: max 2 chunks per document, preserve top-3
4. Filter: threshold finale (0.6) e return top-k

Performance:
- Cross-encoder model lazy loaded (~200MB RAM)
- Batch prediction per latency optimization
- Circuit breaker: skip re-ranking se initial retrieval > 1s
- Fallback: graceful degradation a bi-encoder se error
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings

logger = logging.getLogger("api")

# Lazy import per evitare load torch al startup
_reranker_model = None


def _get_cross_encoder_model(model_name: str):
    """
    Lazy load cross-encoder model.
    
    Model caricato al primo utilizzo (non startup) per evitare
    overhead memoria (~200MB) se feature disabilitata.
    
    Args:
        model_name: Cross-encoder model name (default: ms-marco-MiniLM-L-6-v2)
        
    Returns:
        CrossEncoder model instance
        
    Raises:
        ImportError: Se sentence-transformers non disponibile
    """
    global _reranker_model
    
    if _reranker_model is None:
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info({
                "event": "cross_encoder_loading",
                "model_name": model_name,
            })
            load_start = time.time()
            _reranker_model = CrossEncoder(model_name, max_length=512)
            load_time_ms = int((time.time() - load_start) * 1000)
            
            logger.info({
                "event": "cross_encoder_loaded",
                "model_name": model_name,
                "load_time_ms": load_time_ms,
            })
        except ImportError as exc:
            logger.error({
                "event": "cross_encoder_import_failed",
                "error": str(exc),
                "hint": "Install sentence-transformers: poetry add sentence-transformers@^2.2.2",
            })
            raise
    
    return _reranker_model


class EnhancedChunkRetriever:
    """
    Enhanced chunk retrieval con cross-encoder re-ranking.
    
    Story 7.2 AC1: Pipeline ibrida bi-encoder + cross-encoder.
    
    Usage:
        retriever = EnhancedChunkRetriever(settings)
        results = retriever.retrieve_and_rerank(
            query="dolore lombare",
            match_count=8,
            match_threshold=0.6,
            diversify=True,
        )
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize retriever.
        
        Args:
            settings: Application settings (default: get_settings())
        """
        self.settings = settings or get_settings()
        self._baseline_search = None
    
    @property
    def reranker(self):
        """
        Lazy-loaded cross-encoder model.
        
        Model caricato al primo accesso, non init.
        Memory footprint: ~200MB.
        
        Returns:
            CrossEncoder model instance
        """
        return _get_cross_encoder_model(self.settings.cross_encoder_model_name)
    
    def _get_baseline_search_fn(self):
        """
        Import baseline search function (circular import prevention).
        
        Returns:
            perform_semantic_search function
        """
        if self._baseline_search is None:
            from .search import perform_semantic_search
            self._baseline_search = perform_semantic_search
        return self._baseline_search
    
    def retrieve_and_rerank(
        self,
        query: str,
        match_count: int = 8,
        match_threshold: float = 0.6,
        diversify: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Execute hybrid retrieval pipeline: over-retrieve → re-rank → diversify → filter.
        
        Story 7.2 AC1: Cross-encoder re-ranking implementation.
        
        Pipeline stages:
        1. Over-retrieve: match_count × over_retrieve_factor (default 3x), threshold 0.4
        2. Re-rank: cross-encoder batch prediction (query-chunk pairs)
        3. Diversify: max_per_document enforcement (optional, flag)
        4. Filter: threshold finale (0.6) e limit top-k
        
        Args:
            query: User query string
            match_count: Target number of chunks (default: 8)
            match_threshold: Final threshold post-rerank (default: 0.6)
            diversify: Apply chunk diversification (default: True)
            
        Returns:
            List of chunks con rerank_score, bi_encoder_score, relevance_score
            
        Raises:
            Exception: Propaga errori baseline search (graceful degradation)
        """
        pipeline_start = time.time()
        
        # Stage 1: Over-retrieve con bi-encoder
        over_retrieve_count = match_count * self.settings.cross_encoder_over_retrieve_factor
        over_retrieve_threshold = 0.4  # Lower threshold per recall
        
        logger.info({
            "event": "rerank_pipeline_start",
            "query_preview": query[:100],
            "target_count": match_count,
            "over_retrieve_count": over_retrieve_count,
            "over_retrieve_threshold": over_retrieve_threshold,
        })
        
        retrieval_start = time.time()
        try:
            baseline_search = self._get_baseline_search_fn()
            initial_results = baseline_search(
                query=query,
                match_count=over_retrieve_count,
                match_threshold=over_retrieve_threshold,
            )
        except Exception as exc:
            logger.error({
                "event": "rerank_initial_retrieval_failed",
                "error": str(exc),
            })
            raise  # Propaga per fallback esterno
        
        retrieval_time_ms = int((time.time() - retrieval_start) * 1000)
        
        if not initial_results:
            logger.warning({
                "event": "rerank_no_initial_results",
                "query_preview": query[:100],
            })
            return []
        
        # Circuit breaker: skip re-ranking se retrieval troppo lenta
        if retrieval_time_ms > 1000:
            logger.warning({
                "event": "rerank_circuit_breaker_triggered",
                "retrieval_time_ms": retrieval_time_ms,
                "threshold_ms": 1000,
                "action": "skip_reranking_return_baseline",
            })
            return initial_results[:match_count]
        
        # Stage 2: Re-rank con cross-encoder
        rerank_start = time.time()
        try:
            query_chunk_pairs = [
                [query, chunk.get("content", "")] 
                for chunk in initial_results 
                if chunk.get("content")
            ]
            
            if not query_chunk_pairs:
                logger.warning({
                    "event": "rerank_no_valid_pairs",
                    "initial_results_count": len(initial_results),
                })
                return []
            
            # Batch prediction (20+ pairs per call, latency optimization)
            rerank_scores = self.reranker.predict(query_chunk_pairs, batch_size=32)
            rerank_time_ms = int((time.time() - rerank_start) * 1000)
            
            # Arricchisci chunk con rerank scores
            for idx, chunk in enumerate(initial_results):
                if idx < len(rerank_scores):
                    chunk["rerank_score"] = float(rerank_scores[idx])
                    chunk["bi_encoder_score"] = chunk.get("similarity_score", 0.0)
                    chunk["relevance_score"] = float(rerank_scores[idx])  # Final score = rerank
            
            # Sort per rerank score (descending)
            reranked_results = sorted(
                initial_results,
                key=lambda x: x.get("rerank_score", -1.0),
                reverse=True,
            )
            
            logger.info({
                "event": "rerank_completed",
                "pairs_count": len(query_chunk_pairs),
                "rerank_time_ms": rerank_time_ms,
                "scores_min": float(min(rerank_scores)) if rerank_scores.size > 0 else None,
                "scores_max": float(max(rerank_scores)) if rerank_scores.size > 0 else None,
                "scores_avg": float(rerank_scores.mean()) if rerank_scores.size > 0 else None,
            })
            
        except Exception as exc:
            logger.warning({
                "event": "rerank_failed_fallback_baseline",
                "error": str(exc),
                "action": "return_baseline_results",
            })
            # Fallback: return bi-encoder results
            return initial_results[:match_count]
        
        # Stage 3: Diversification (optional)
        diversified_results = reranked_results
        if diversify and self.settings.enable_chunk_diversification:
            from .diversification import diversify_chunks, calculate_diversity_score
            
            diversity_before = calculate_diversity_score(reranked_results[:match_count])
            diversified_results = diversify_chunks(
                chunks=reranked_results,
                max_per_doc=self.settings.diversification_max_per_document,
                preserve_top_n=self.settings.diversification_preserve_top_n,
            )
            diversity_after = calculate_diversity_score(diversified_results[:match_count])
            
            logger.info({
                "event": "diversification_applied",
                "diversity_score_before": round(diversity_before, 3),
                "diversity_score_after": round(diversity_after, 3),
                "improvement": round(diversity_after - diversity_before, 3),
            })
        
        # Stage 4: Filter per threshold finale e limit top-k
        final_threshold = match_threshold or self.settings.cross_encoder_threshold_post_rerank
        filtered_results = [
            chunk for chunk in diversified_results
            if chunk.get("rerank_score", 0.0) >= final_threshold
        ][:match_count]
        
        pipeline_time_ms = int((time.time() - pipeline_start) * 1000)
        
        logger.info({
            "event": "rerank_pipeline_complete",
            "total_time_ms": pipeline_time_ms,
            "retrieval_time_ms": retrieval_time_ms,
            "rerank_time_ms": rerank_time_ms,
            "initial_count": len(initial_results),
            "reranked_count": len(reranked_results),
            "diversified_count": len(diversified_results),
            "final_count": len(filtered_results),
            "final_threshold": final_threshold,
        })
        
        return filtered_results


def get_enhanced_retriever(settings: Optional[Settings] = None) -> EnhancedChunkRetriever:
    """
    Factory function per EnhancedChunkRetriever.
    
    Args:
        settings: Application settings (default: get_settings())
        
    Returns:
        EnhancedChunkRetriever instance
    """
    return EnhancedChunkRetriever(settings=settings)

