# Cross-Encoder Testing & Validation Guide

**Document Type**: Testing Guide  
**Date**: 2025-10-22  
**Related**: Story 7.1 Task 6

---

## Test Strategy

### Unit Tests

**File**: `apps/api/tests/knowledge_base/test_enhanced_retrieval.py`

```python
import pytest
from unittest.mock import Mock, patch
from api.knowledge_base.enhanced_retrieval import EnhancedChunkRetriever


def test_reranker_lazy_loading():
    """Verify cross-encoder loads only on first use."""
    retriever = EnhancedChunkRetriever()
    assert retriever._reranker is None
    
    # Trigger load
    _ = retriever.reranker
    assert retriever._reranker is not None


def test_retrieve_and_rerank_basic(mock_search, mock_cross_encoder):
    """Test basic re-ranking pipeline."""
    # Mock initial search
    mock_search.return_value = [
        {"id": "1", "content": "relevant", "similarity_score": 0.7},
        {"id": "2", "content": "less relevant", "similarity_score": 0.65}
    ]
    
    # Mock cross-encoder scores (reversed order)
    mock_cross_encoder.predict.return_value = [0.9, 0.5]
    
    retriever = EnhancedChunkRetriever()
    results = retriever.retrieve_and_rerank("test query", match_count=2)
    
    # Verify re-ranking reversed order
    assert results[0]["id"] == "1"
    assert results[0]["rerank_score"] == 0.9
    assert results[1]["id"] == "2"


def test_diversification():
    """Test chunk diversification per document."""
    retriever = EnhancedChunkRetriever()
    chunks = [
        {"id": "1", "document_id": "doc1", "rerank_score": 0.9},
        {"id": "2", "document_id": "doc1", "rerank_score": 0.85},
        {"id": "3", "document_id": "doc1", "rerank_score": 0.8},  # Should be filtered
        {"id": "4", "document_id": "doc2", "rerank_score": 0.75},
    ]
    
    diversified = retriever._diversify_by_document(chunks, max_per_document=2)
    
    assert len(diversified) == 3
    doc1_count = sum(1 for c in diversified if c["document_id"] == "doc1")
    assert doc1_count == 2


def test_threshold_filtering():
    """Test relevance threshold filtering."""
    with patch('api.knowledge_base.search.perform_semantic_search') as mock_search:
        mock_search.return_value = [
            {"content": "high", "similarity_score": 0.8},
            {"content": "low", "similarity_score": 0.3}
        ]
        
        retriever = EnhancedChunkRetriever()
        with patch.object(retriever, 'reranker') as mock_reranker:
            mock_reranker.predict.return_value = [0.9, 0.4]
            
            results = retriever.retrieve_and_rerank(
                "query",
                match_count=10,
                match_threshold=0.6
            )
            
            # Only high-scoring result should pass
            assert len(results) == 1
            assert results[0]["rerank_score"] == 0.9
```

---

## Integration Tests

```python
@pytest.mark.integration
async def test_rerank_e2e_real_model():
    """
    E2E test con modello reale (slow, run con --run-integration).
    
    Verifica:
    - Model loading funziona
    - Re-ranking migliora ordine risultati
    - Latency accettabile
    """
    import time
    from api.knowledge_base.enhanced_retrieval import get_enhanced_retriever
    
    retriever = get_enhanced_retriever()
    query = "sintomi spondilolistesi lombare"
    
    start = time.time()
    results = retriever.retrieve_and_rerank(
        query=query,
        match_count=5,
        match_threshold=0.5
    )
    latency_ms = int((time.time() - start) * 1000)
    
    # Assertions
    assert len(results) > 0, "Should retrieve results"
    assert all('rerank_score' in r for r in results), "Should have rerank scores"
    assert latency_ms < 2000, f"Latency {latency_ms}ms exceeds 2s threshold"
    
    # Verify descending order
    scores = [r['rerank_score'] for r in results]
    assert scores == sorted(scores, reverse=True), "Should be sorted by score"
```

---

## Benchmark Tests

### Precision Measurement

```python
def test_precision_at_k_benchmark():
    """
    Benchmark precision@k con ground truth manuale.
    
    Dataset: 50 query rappresentative da analytics studenti
    Ground truth: annotazioni manuali docenti (top-5 rilevanti)
    """
    from api.knowledge_base.enhanced_retrieval import get_enhanced_retriever
    from api.knowledge_base.search import perform_semantic_search
    
    # Load benchmark dataset
    benchmark_queries = load_benchmark_dataset()  # 50 query + ground truth
    
    retriever = get_enhanced_retriever()
    
    precision_baseline = []
    precision_enhanced = []
    
    for item in benchmark_queries:
        query = item['query']
        ground_truth_ids = set(item['relevant_chunk_ids'])
        
        # Baseline (bi-encoder only)
        baseline_results = perform_semantic_search(query, match_count=5)
        baseline_ids = set(r['id'] for r in baseline_results)
        baseline_hits = len(baseline_ids & ground_truth_ids)
        precision_baseline.append(baseline_hits / 5.0)
        
        # Enhanced (with re-ranking)
        enhanced_results = retriever.retrieve_and_rerank(query, match_count=5)
        enhanced_ids = set(r['id'] for r in enhanced_results)
        enhanced_hits = len(enhanced_ids & ground_truth_ids)
        precision_enhanced.append(enhanced_hits / 5.0)
    
    # Calculate average precision@5
    avg_precision_baseline = sum(precision_baseline) / len(precision_baseline)
    avg_precision_enhanced = sum(precision_enhanced) / len(precision_enhanced)
    
    improvement = ((avg_precision_enhanced - avg_precision_baseline) / avg_precision_baseline) * 100
    
    print(f"Precision@5 Baseline: {avg_precision_baseline:.3f}")
    print(f"Precision@5 Enhanced: {avg_precision_enhanced:.3f}")
    print(f"Improvement: +{improvement:.1f}%")
    
    # Assert minimum improvement
    assert avg_precision_enhanced > avg_precision_baseline, "Re-ranking should improve precision"
    assert improvement >= 15, f"Expected >=15% improvement, got {improvement:.1f}%"
```

### Latency Benchmark

```python
def test_latency_percentiles():
    """
    Misura distribuzione latenza re-ranking.
    
    Target: p95 < 2000ms (retrieval completo)
    """
    import time
    import numpy as np
    
    retriever = get_enhanced_retriever()
    queries = [
        "spondilolistesi grading meyerding",
        "stenosi spinale lombare sintomi",
        "radicolopatia L5 S1 trattamento",
        # ... 20 query totali
    ]
    
    latencies_ms = []
    
    for query in queries:
        start = time.time()
        results = retriever.retrieve_and_rerank(query, match_count=8)
        duration_ms = int((time.time() - start) * 1000)
        latencies_ms.append(duration_ms)
    
    p50 = np.percentile(latencies_ms, 50)
    p95 = np.percentile(latencies_ms, 95)
    p99 = np.percentile(latencies_ms, 99)
    
    print(f"Latency p50: {p50:.0f}ms")
    print(f"Latency p95: {p95:.0f}ms")
    print(f"Latency p99: {p99:.0f}ms")
    
    # Assert SLO
    assert p95 < 2000, f"p95 latency {p95}ms exceeds 2s SLO"
```

---

## Manual Validation

### Sample Queries

Eseguire retrieval manuale con queste query rappresentative:

```python
test_queries = [
    {
        "query": "sintomi spondilolistesi lombare",
        "expected_concepts": ["scivolamento vertebrale", "L5-S1", "dolore lombare"],
        "expected_min_score": 0.75
    },
    {
        "query": "differenza spondilolisi spondilolistesi",
        "expected_concepts": ["istmica", "scivolamento", "displasia"],
        "expected_min_score": 0.70
    },
    {
        "query": "grading meyerding classificazione",
        "expected_concepts": ["percentuale", "I-IV", "antero-posteriore"],
        "expected_min_score": 0.80
    },
]

for test in test_queries:
    results = retriever.retrieve_and_rerank(test["query"], match_count=5)
    print(f"\nQuery: {test['query']}")
    print(f"Top result score: {results[0]['rerank_score']:.3f}")
    print(f"Top content: {results[0]['content'][:100]}...")
    
    # Manual check: do results contain expected concepts?
    for concept in test["expected_concepts"]:
        found = any(concept.lower() in r['content'].lower() for r in results)
        print(f"  - Concept '{concept}': {'✅ Found' if found else '❌ Missing'}")
```

---

## Regression Testing

### Baseline Snapshots

Prima di deploy, catturare snapshot risultati baseline:

```python
# Generate baseline snapshot
baseline_results = {}
for query in standard_test_queries:
    results = perform_semantic_search(query, match_count=5)
    baseline_results[query] = [r['id'] for r in results]

save_snapshot('baseline_v1.json', baseline_results)

# After re-ranking implementation
enhanced_results = {}
for query in standard_test_queries:
    results = retriever.retrieve_and_rerank(query, match_count=5)
    enhanced_results[query] = [r['id'] for r in results]

save_snapshot('enhanced_v1.json', enhanced_results)

# Compare snapshots
compare_snapshots('baseline_v1.json', 'enhanced_v1.json')
```

---

## Monitoring in Production

### Metrics da Tracciare

```python
# apps/api/api/analytics/retrieval_metrics.py

rerank_metrics = {
    "total_requests": Counter,
    "latency_ms": Histogram(buckets=[100, 300, 500, 1000, 2000]),
    "rerank_score_avg": Gauge,
    "fallback_count": Counter,
    "documents_diversity_avg": Gauge,
}

# Log dopo ogni rerank
logger.info({
    "event": "rerank_metrics",
    "latency_ms": duration,
    "score_distribution": {
        "min": min(scores),
        "max": max(scores),
        "avg": avg(scores)
    },
    "documents_diversity": len(unique_doc_ids)
})
```

### Alerts

- Latency p95 > 2s per 5min
- Fallback rate > 5% per 10min
- Average rerank score < 0.5 (possibile model issue)

---

## Ground Truth Dataset

### Creation

```python
# Script per creare dataset annotato
# apps/api/scripts/create_rerank_benchmark.py

import random
from api.knowledge_base.search import perform_semantic_search

# 1. Sample query reali da analytics
queries = sample_real_queries(n=50)

# 2. Per ogni query, recupera top-20 chunk
benchmark_data = []
for query in queries:
    results = perform_semantic_search(query, match_count=20)
    
    benchmark_item = {
        "query": query,
        "candidate_chunks": [
            {
                "id": r['id'],
                "content": r['content'],
                "document_name": r.get('metadata', {}).get('document_name')
            }
            for r in results
        ],
        "relevant_chunk_ids": []  # Da annotare manualmente
    }
    benchmark_data.append(benchmark_item)

save_json('benchmark_dataset_raw.json', benchmark_data)
```

### Annotation Guidelines

Per ogni query, marcare come rilevanti chunk che:
- Rispondono direttamente alla domanda
- Contengono informazioni essenziali per risposta completa
- Sono accurati medicalmente

Tipicamente 3-5 chunk rilevanti per query su top-20.

---

## References

- MS MARCO Evaluation: https://github.com/microsoft/MSMARCO-Passage-Ranking
- BEIR Benchmark: https://github.com/beir-cellar/beir
- Sentence Transformers Evaluation: https://www.sbert.net/docs/package_reference/evaluation.html
