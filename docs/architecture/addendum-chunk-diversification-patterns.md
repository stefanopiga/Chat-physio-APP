# Chunk Diversification Patterns

**Document Type**: Technical Reference  
**Date**: 2025-10-22  
**Status**: Approved  
**Related**: Story 7.1 Task 3

---

## Problem Statement

**Issue**: Semantic search può ritornare chunk ridondanti dallo stesso documento.

**Example scenario**:
```
Query: "spondilolistesi trattamento"

Top-8 results (no diversification):
1. Doc A p.12: "La spondilolistesi..."         score: 0.92
2. Doc A p.13: "Nel trattamento della..."      score: 0.90
3. Doc A p.14: "Il paziente con..."            score: 0.88
4. Doc A p.15: "Approccio riabilitativo..."    score: 0.87
5. Doc A p.16: "Esercizi specifici..."         score: 0.85
6. Doc B p.5:  "Classificazione..."            score: 0.83
7. Doc A p.17: "Progressione carico..."        score: 0.82
8. Doc A p.18: "Follow-up..."                  score: 0.80
```

**Consequence**:
- ❌ 7/8 chunk da Doc A → context window sprecato su singolo documento
- ❌ 1/8 chunk da Doc B → coverage multi-documento insufficiente
- ❌ Prospettive alternative/complementari perse

**Target**: Max 2 chunk per documento nei top-k finali → migliore coverage.

---

## Implementation

### Diversification Algorithm

```python
# apps/api/api/knowledge_base/diversification.py

from typing import List, Dict, Any
from collections import defaultdict


def diversify_chunks(
    chunks: List[Dict[str, Any]],
    max_per_document: int = 2,
    preserve_top_n: int = 3
) -> List[Dict[str, Any]]:
    """
    Diversifica chunk per documento mantenendo relevance order.
    
    Algorithm:
    1. Preserve top N chunk indipendentemente da documento (garantire precision)
    2. Per chunk rimanenti, applica diversification limit
    3. Mantieni ordine relevance originale
    
    Args:
        chunks: Lista chunk ordinati per relevance score (descending)
        max_per_document: Max chunk dallo stesso documento
        preserve_top_n: Numero top chunk da non diversificare (precision guarantee)
        
    Returns:
        Lista diversificata mantenendo ordine relevance
        
    Example:
        Input:  [DocA(0.9), DocA(0.85), DocA(0.8), DocB(0.75), DocA(0.7)]
        Output: [DocA(0.9), DocA(0.85), DocB(0.75), DocA(0.7)]  
                # 3rd DocA chunk (0.8) rimosso per diversification
    """
    if not chunks:
        return []
    
    # Step 1: Preserve top N unconditionally
    preserved_chunks = chunks[:preserve_top_n]
    remaining_chunks = chunks[preserve_top_n:]
    
    # Step 2: Diversify remaining chunks
    document_counts: Dict[str, int] = defaultdict(int)
    
    # Count documents in preserved chunks
    for chunk in preserved_chunks:
        doc_id = chunk.get('document_id', 'unknown')
        document_counts[doc_id] += 1
    
    # Diversify remaining
    diversified_remaining = []
    for chunk in remaining_chunks:
        doc_id = chunk.get('document_id', 'unknown')
        count = document_counts[doc_id]
        
        if count < max_per_document:
            diversified_remaining.append(chunk)
            document_counts[doc_id] += 1
    
    # Combine preserved + diversified
    result = preserved_chunks + diversified_remaining
    
    return result


def get_document_distribution(chunks: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calcola distribuzione chunk per documento.
    
    Returns:
        {document_id: chunk_count}
    """
    distribution = defaultdict(int)
    for chunk in chunks:
        doc_id = chunk.get('document_id', 'unknown')
        distribution[doc_id] += 1
    return dict(distribution)


def calculate_diversity_score(chunks: List[Dict[str, Any]]) -> float:
    """
    Calcola diversity score: numero documenti unici / totale chunk.
    
    Returns:
        Score 0.0-1.0 (1.0 = massima diversità, tutti chunk da doc diversi)
        
    Example:
        8 chunk da 4 documenti → 4/8 = 0.5
        8 chunk da 8 documenti → 8/8 = 1.0
    """
    if not chunks:
        return 0.0
    
    unique_docs = len(set(c.get('document_id', 'unknown') for c in chunks))
    total_chunks = len(chunks)
    
    return unique_docs / total_chunks
```

---

## Integration with Enhanced Retriever

### Update EnhancedChunkRetriever

```python
# apps/api/api/knowledge_base/enhanced_retrieval.py

from .diversification import diversify_chunks, calculate_diversity_score

class EnhancedChunkRetriever:
    # ... existing code ...
    
    def retrieve_and_rerank(
        self,
        query: str,
        match_count: int = 8,
        match_threshold: float = 0.6,
        diversify: bool = True,
        max_per_document: int = 2,
    ) -> List[Dict[str, Any]]:
        """Enhanced retrieval with diversification."""
        
        # ... initial retrieval + re-ranking ...
        
        # Diversify if enabled
        if diversify:
            before_diversity = calculate_diversity_score(reranked_chunks)
            
            diversified = diversify_chunks(
                reranked_chunks,
                max_per_document=max_per_document,
                preserve_top_n=3  # Always keep top 3 for precision
            )
            
            after_diversity = calculate_diversity_score(diversified)
            
            logger.debug({
                "event": "diversification_applied",
                "before_diversity_score": before_diversity,
                "after_diversity_score": after_diversity,
                "improvement": after_diversity - before_diversity
            })
            
            reranked_chunks = diversified
        
        # ... final threshold and return ...
```

---

## Trade-offs Analysis

### Precision vs Diversity

**Scenario**: Top-3 risultati sono tutti da stesso documento (score 0.95, 0.93, 0.91).

**Without diversification**:
- ✅ Massima precision (tutti top score)
- ❌ Nessuna prospettiva alternativa

**With diversification (preserve_top_n=3)**:
- ✅ Precision preservata (top-3 unchanged)
- ✅ Chunk 4-10 diversificati → coverage multi-doc

**Conclusion**: Preserving top N chunks garantisce best precision mentre diversifica resto.

---

## Examples

### Example 1: Heavy Redundancy

**Input** (10 chunk, query "spondilolistesi"):
```
1. DocA p.12  score:0.92
2. DocA p.13  score:0.90
3. DocA p.14  score:0.88
4. DocB p.5   score:0.86
5. DocA p.15  score:0.84
6. DocA p.16  score:0.82
7. DocC p.8   score:0.80
8. DocA p.17  score:0.78
9. DocD p.3   score:0.76
10. DocA p.18 score:0.74
```

**Distribution before**:
- DocA: 7 chunk
- DocB: 1 chunk
- DocC: 1 chunk
- DocD: 1 chunk
- **Diversity score**: 4/10 = 0.40

**After diversification** (max_per_document=2, preserve_top_n=3):
```
1. DocA p.12  score:0.92  ← preserved (top 3)
2. DocA p.13  score:0.90  ← preserved (top 3)
3. DocA p.14  score:0.88  ← preserved (top 3) [DocA count: 3/2 exceeded but preserved]
4. DocB p.5   score:0.86  ← kept (DocB: 1/2)
5. DocC p.8   score:0.80  ← kept (DocC: 1/2)
6. DocD p.3   score:0.76  ← kept (DocD: 1/2)
   [DocA chunks 5,6,8,10 removed - already 3 from DocA]
```

**Distribution after**:
- DocA: 3 chunk (preserved top 3)
- DocB: 1 chunk
- DocC: 1 chunk
- DocD: 1 chunk
- **Diversity score**: 4/6 = 0.67 (+68% improvement)

**Trade-off**: 10 chunk → 6 chunk finale (lost 4 DocA redundant) but +68% diversity.

---

## Advanced: Content-Based Diversification

### Phase 2 Enhancement

```python
def semantic_diversify_chunks(
    chunks: List[Dict[str, Any]],
    similarity_threshold: float = 0.85,
    max_similar_chunks: int = 2
) -> List[Dict[str, Any]]:
    """
    Diversification basata su similarità contenuto (non solo document_id).
    
    Rimuove chunk troppo simili tra loro anche se da documenti diversi.
    
    Algorithm:
    1. Calcola similarity matrix tra tutti chunk (cosine similarity embeddings)
    2. Per ogni chunk, trova chunk troppo simili (> threshold)
    3. Mantieni solo max_similar_chunks chunk simili tra loro
    
    Use case: Due documenti diversi con paragrafi quasi identici
    (es. slide copiata in 2 set diversi).
    """
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    
    # Extract embeddings (assume disponibili nei chunk)
    embeddings = np.array([c['embedding'] for c in chunks])
    
    # Similarity matrix
    sim_matrix = cosine_similarity(embeddings)
    
    # Diversify
    kept_indices = []
    for i in range(len(chunks)):
        # Count similar chunks già mantenuti
        similar_count = sum(
            1 for j in kept_indices 
            if sim_matrix[i][j] > similarity_threshold
        )
        
        if similar_count < max_similar_chunks:
            kept_indices.append(i)
    
    return [chunks[i] for i in kept_indices]
```

**Trade-off**: Più computazionale (similarity matrix) ma migliore semantic diversity.

---

## Monitoring

### Metrics

```python
# Track diversification effectiveness
diversification_metrics = {
    "diversity_score_before": Gauge,
    "diversity_score_after": Gauge,
    "diversity_improvement": Gauge,  # after - before
    "avg_docs_per_query": Gauge,
    "chunks_removed_count": Counter,
}

# Log per ogni diversification
logger.info({
    "event": "diversification_metrics",
    "query": query[:100],
    "before": {
        "chunk_count": len(reranked_chunks),
        "unique_docs": len(set(c['document_id'] for c in reranked_chunks)),
        "diversity_score": before_diversity
    },
    "after": {
        "chunk_count": len(diversified),
        "unique_docs": len(set(c['document_id'] for c in diversified)),
        "diversity_score": after_diversity
    },
    "improvement_pct": ((after_diversity - before_diversity) / before_diversity) * 100
})
```

### Dashboard

**Grafana panel**:
- Diversity score time series (before/after)
- Document distribution histogram
- Chunks removed per query (avg)

---

## Configuration

```python
# apps/api/api/config.py

class Settings(BaseSettings):
    # ...
    
    enable_chunk_diversification: bool = Field(
        default=True,
        env="ENABLE_CHUNK_DIVERSIFICATION"
    )
    
    diversification_max_per_document: int = Field(
        default=2,
        ge=1,
        le=5,
        env="DIVERSIFICATION_MAX_PER_DOCUMENT",
        description="Max chunk per documento in risultati finali"
    )
    
    diversification_preserve_top_n: int = Field(
        default=3,
        ge=1,
        le=5,
        env="DIVERSIFICATION_PRESERVE_TOP_N",
        description="Top N chunk da preservare indipendentemente da diversification"
    )
```

---

## Testing

```python
# tests/knowledge_base/test_diversification.py

def test_diversify_removes_excess_chunks():
    """Test rimozione chunk eccedenti da stesso documento."""
    chunks = [
        {"id": "1", "document_id": "docA", "score": 0.9},
        {"id": "2", "document_id": "docA", "score": 0.85},
        {"id": "3", "document_id": "docA", "score": 0.8},  # Should be removed
        {"id": "4", "document_id": "docB", "score": 0.75},
    ]
    
    diversified = diversify_chunks(chunks, max_per_document=2, preserve_top_n=0)
    
    assert len(diversified) == 3
    doc_a_count = sum(1 for c in diversified if c["document_id"] == "docA")
    assert doc_a_count == 2


def test_preserves_top_n():
    """Test preservation top N chunk."""
    chunks = [
        {"id": "1", "document_id": "docA", "score": 0.9},
        {"id": "2", "document_id": "docA", "score": 0.88},
        {"id": "3", "document_id": "docA", "score": 0.86},  # 3rd from docA
        {"id": "4", "document_id": "docB", "score": 0.84},
    ]
    
    # Preserve top 3 → all 3 docA chunks kept despite max_per_document=2
    diversified = diversify_chunks(chunks, max_per_document=2, preserve_top_n=3)
    
    assert len(diversified) == 4  # All preserved (top 3) + docB
    assert diversified[0]["id"] == "1"
    assert diversified[1]["id"] == "2"
    assert diversified[2]["id"] == "3"


def test_diversity_score_calculation():
    """Test diversity score metric."""
    chunks = [
        {"document_id": "A"},
        {"document_id": "A"},
        {"document_id": "B"},
        {"document_id": "C"},
    ]
    
    # 3 unique docs / 4 total chunks = 0.75
    score = calculate_diversity_score(chunks)
    assert score == 0.75
```

---

## Best Practices

### 1. Balance Precision & Diversity

```python
# Preserve top-3 always per garantire precision
PRESERVE_TOP_N = 3

# Max 2 chunk per doc nel resto dei risultati
MAX_PER_DOCUMENT = 2
```

### 2. Log Distribution per Debug

```python
distribution = get_document_distribution(final_chunks)
logger.info({
    "event": "chunk_distribution",
    "query": query[:100],
    "distribution": distribution,
    "unique_documents": len(distribution)
})
```

### 3. A/B Test Impact

```python
# Test diversification impact on user satisfaction
ab_test_config = {
    "control": {"diversify": False},
    "treatment": {"diversify": True, "max_per_document": 2}
}

# Metrics: completeness perceived, follow-up rate, satisfaction
```

---

## References

- Carbonell & Goldstein (1998): "Maximal Marginal Relevance" (MMR algorithm)
- Clarke et al. (2008): "Novelty and Diversity in Information Retrieval"
- Zhai et al. (2003): "Beyond Independent Relevance: A Study of Diversity"
