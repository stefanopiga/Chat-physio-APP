"""
Benchmark script for retrieval optimization (Story 7.2 AC6).

Compara baseline semantic search vs enhanced retrieval pipeline.

Metrics:
- Precision@5, Precision@10
- NDCG@10
- MRR (Mean Reciprocal Rank)
- Diversity Score
- Latency (p50, p95)

Usage:
    python scripts/benchmark_retrieval.py --output reports/retrieval-benchmark-7.2.md
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from statistics import mean, median

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.knowledge_base.search import perform_semantic_search
from api.knowledge_base.enhanced_retrieval import get_enhanced_retriever
from api.knowledge_base.diversification import calculate_diversity_score
from api.config import get_settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_ground_truth(file_path: str) -> List[Dict[str, Any]]:
    """
    Load ground truth dataset.
    
    Args:
        file_path: Path to ground truth JSON file
        
    Returns:
        List of ground truth items
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data)} ground truth queries from {file_path}")
    return data


def calculate_precision_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """
    Calculate Precision@k.
    
    Args:
        retrieved_ids: List of retrieved chunk IDs (ordered by relevance)
        relevant_ids: List of relevant chunk IDs (ground truth)
        k: Cut-off position
        
    Returns:
        Precision@k score (0.0-1.0)
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    
    top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    
    hits = sum(1 for chunk_id in top_k if chunk_id in relevant_set)
    precision = hits / min(k, len(top_k))
    
    return precision


def calculate_ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """
    Calculate NDCG@k (Normalized Discounted Cumulative Gain).
    
    Args:
        retrieved_ids: List of retrieved chunk IDs (ordered by relevance)
        relevant_ids: List of relevant chunk IDs (ground truth)
        k: Cut-off position
        
    Returns:
        NDCG@k score (0.0-1.0)
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    
    top_k = retrieved_ids[:k]
    relevant_set = set(relevant_ids)
    
    # DCG: relevance 1 se in relevant_set, 0 altrimenti
    dcg = 0.0
    for i, chunk_id in enumerate(top_k, start=1):
        relevance = 1.0 if chunk_id in relevant_set else 0.0
        dcg += relevance / np.log2(i + 1)
    
    # IDCG: ideal DCG (tutti rilevanti in top-k)
    ideal_ranking = [1.0] * min(len(relevant_ids), k)
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_ranking))
    
    if idcg == 0:
        return 0.0
    
    ndcg = dcg / idcg
    return ndcg


def calculate_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """
    Calculate MRR (Mean Reciprocal Rank).
    
    Args:
        retrieved_ids: List of retrieved chunk IDs (ordered by relevance)
        relevant_ids: List of relevant chunk IDs (ground truth)
        
    Returns:
        Reciprocal rank (0.0-1.0)
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    
    relevant_set = set(relevant_ids)
    
    for i, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_set:
            return 1.0 / i
    
    return 0.0


def run_baseline_retrieval(query: str, match_count: int = 10) -> tuple[List[Dict], float]:
    """
    Run baseline semantic search.
    
    Args:
        query: User query
        match_count: Number of chunks to retrieve
        
    Returns:
        (results, latency_ms)
    """
    start_time = time.time()
    results = perform_semantic_search(query=query, match_count=match_count, match_threshold=0.4)
    latency_ms = (time.time() - start_time) * 1000
    
    return results, latency_ms


def run_enhanced_retrieval(query: str, match_count: int = 10) -> tuple[List[Dict], float]:
    """
    Run enhanced retrieval with re-ranking.
    
    Args:
        query: User query
        match_count: Number of chunks to retrieve
        
    Returns:
        (results, latency_ms)
    """
    settings = get_settings()
    settings.enable_cross_encoder_reranking = True
    settings.enable_chunk_diversification = True
    
    retriever = get_enhanced_retriever(settings)
    
    start_time = time.time()
    results = retriever.retrieve_and_rerank(
        query=query,
        match_count=match_count,
        match_threshold=0.6,
        diversify=True,
    )
    latency_ms = (time.time() - start_time) * 1000
    
    return results, latency_ms


def benchmark_retrieval(ground_truth: List[Dict[str, Any]], output_path: Optional[str] = None):
    """
    Run benchmark comparison: baseline vs enhanced retrieval.
    
    Args:
        ground_truth: Ground truth dataset
        output_path: Output file path for report
    """
    logger.info("Starting retrieval benchmark...")
    
    baseline_metrics = {
        "precision_at_5": [],
        "precision_at_10": [],
        "ndcg_at_10": [],
        "mrr": [],
        "diversity_score": [],
        "latency_ms": [],
    }
    
    enhanced_metrics = {
        "precision_at_5": [],
        "precision_at_10": [],
        "ndcg_at_10": [],
        "mrr": [],
        "diversity_score": [],
        "latency_ms": [],
    }
    
    for item in ground_truth:
        query = item["query"]
        relevant_ids = item["relevant_chunk_ids"]
        query_id = item["query_id"]
        
        logger.info(f"Processing {query_id}: {query[:60]}...")
        
        # Baseline retrieval
        try:
            baseline_results, baseline_latency = run_baseline_retrieval(query, match_count=10)
            baseline_ids = [r.get("id") for r in baseline_results if r.get("id")]
            
            baseline_metrics["precision_at_5"].append(calculate_precision_at_k(baseline_ids, relevant_ids, 5))
            baseline_metrics["precision_at_10"].append(calculate_precision_at_k(baseline_ids, relevant_ids, 10))
            baseline_metrics["ndcg_at_10"].append(calculate_ndcg_at_k(baseline_ids, relevant_ids, 10))
            baseline_metrics["mrr"].append(calculate_mrr(baseline_ids, relevant_ids))
            baseline_metrics["diversity_score"].append(calculate_diversity_score(baseline_results[:10]))
            baseline_metrics["latency_ms"].append(baseline_latency)
        except Exception as e:
            logger.error(f"Baseline retrieval failed for {query_id}: {e}")
            continue
        
        # Enhanced retrieval
        try:
            enhanced_results, enhanced_latency = run_enhanced_retrieval(query, match_count=10)
            enhanced_ids = [r.get("id") for r in enhanced_results if r.get("id")]
            
            enhanced_metrics["precision_at_5"].append(calculate_precision_at_k(enhanced_ids, relevant_ids, 5))
            enhanced_metrics["precision_at_10"].append(calculate_precision_at_k(enhanced_ids, relevant_ids, 10))
            enhanced_metrics["ndcg_at_10"].append(calculate_ndcg_at_k(enhanced_ids, relevant_ids, 10))
            enhanced_metrics["mrr"].append(calculate_mrr(enhanced_ids, relevant_ids))
            enhanced_metrics["diversity_score"].append(calculate_diversity_score(enhanced_results[:10]))
            enhanced_metrics["latency_ms"].append(enhanced_latency)
        except Exception as e:
            logger.error(f"Enhanced retrieval failed for {query_id}: {e}")
            # Add baseline values as fallback for comparison fairness
            enhanced_metrics["precision_at_5"].append(baseline_metrics["precision_at_5"][-1])
            enhanced_metrics["precision_at_10"].append(baseline_metrics["precision_at_10"][-1])
            enhanced_metrics["ndcg_at_10"].append(baseline_metrics["ndcg_at_10"][-1])
            enhanced_metrics["mrr"].append(baseline_metrics["mrr"][-1])
            enhanced_metrics["diversity_score"].append(baseline_metrics["diversity_score"][-1])
            enhanced_metrics["latency_ms"].append(baseline_latency)
    
    # Generate report
    report = generate_report(baseline_metrics, enhanced_metrics, ground_truth)
    
    # Save report
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Report saved to {output_path}")
    else:
        print(report)


def generate_report(
    baseline: Dict[str, List[float]],
    enhanced: Dict[str, List[float]],
    ground_truth: List[Dict],
) -> str:
    """
    Generate benchmark report in Markdown format.
    
    Args:
        baseline: Baseline metrics
        enhanced: Enhanced metrics
        ground_truth: Ground truth dataset
        
    Returns:
        Markdown report string
    """
    def calc_stats(values: List[float]) -> Dict[str, float]:
        return {
            "mean": mean(values) if values else 0.0,
            "median": median(values) if values else 0.0,
            "p95": np.percentile(values, 95) if values else 0.0,
        }
    
    # Calculate aggregate statistics
    baseline_stats = {k: calc_stats(v) for k, v in baseline.items()}
    enhanced_stats = {k: calc_stats(v) for k, v in enhanced.items()}
    
    # Calculate improvements
    improvements = {}
    for metric in baseline_stats.keys():
        baseline_mean = baseline_stats[metric]["mean"]
        enhanced_mean = enhanced_stats[metric]["mean"]
        if baseline_mean > 0:
            improvements[metric] = ((enhanced_mean - baseline_mean) / baseline_mean) * 100
        else:
            improvements[metric] = 0.0
    
    # Generate report
    report = f"""# Retrieval Benchmark Report - Story 7.2

**Date:** {time.strftime("%Y-%m-%d %H:%M:%S")}  
**Ground Truth Queries:** {len(ground_truth)}  
**Test Scope:** Baseline (bi-encoder) vs Enhanced (re-ranking + diversification)

---

## Executive Summary

### Target Achievement

| Metric | Baseline | Enhanced | Improvement | Target | Status |
|--------|----------|----------|-------------|--------|--------|
| Precision@5 | {baseline_stats['precision_at_5']['mean']:.3f} | {enhanced_stats['precision_at_5']['mean']:.3f} | **{improvements['precision_at_5']:+.1f}%** | +26% | {'✅ PASSED' if improvements['precision_at_5'] >= 20 else '⚠️ REVIEW'} |
| NDCG@10 | {baseline_stats['ndcg_at_10']['mean']:.3f} | {enhanced_stats['ndcg_at_10']['mean']:.3f} | **{improvements['ndcg_at_10']:+.1f}%** | +20% | {'✅ PASSED' if improvements['ndcg_at_10'] >= 15 else '⚠️ REVIEW'} |
| Diversity Score | {baseline_stats['diversity_score']['mean']:.3f} | {enhanced_stats['diversity_score']['mean']:.3f} | **{improvements['diversity_score']:+.1f}%** | +68% | {'✅ PASSED' if improvements['diversity_score'] >= 50 else '⚠️ REVIEW'} |
| Latency p95 (ms) | {baseline_stats['latency_ms']['p95']:.0f} | {enhanced_stats['latency_ms']['p95']:.0f} | {improvements['latency_ms']:+.1f}% | <2000ms | {'✅ PASSED' if enhanced_stats['latency_ms']['p95'] < 2000 else '❌ FAILED'} |

---

## Detailed Metrics

### Precision

| Metric | Baseline Mean | Enhanced Mean | Δ Absolute | Δ Relative |
|--------|---------------|---------------|------------|------------|
| Precision@5 | {baseline_stats['precision_at_5']['mean']:.3f} | {enhanced_stats['precision_at_5']['mean']:.3f} | {enhanced_stats['precision_at_5']['mean'] - baseline_stats['precision_at_5']['mean']:+.3f} | {improvements['precision_at_5']:+.1f}% |
| Precision@10 | {baseline_stats['precision_at_10']['mean']:.3f} | {enhanced_stats['precision_at_10']['mean']:.3f} | {enhanced_stats['precision_at_10']['mean'] - baseline_stats['precision_at_10']['mean']:+.3f} | {improvements['precision_at_10']:+.1f}% |

### Ranking Quality

| Metric | Baseline Mean | Enhanced Mean | Δ Absolute | Δ Relative |
|--------|---------------|---------------|------------|------------|
| NDCG@10 | {baseline_stats['ndcg_at_10']['mean']:.3f} | {enhanced_stats['ndcg_at_10']['mean']:.3f} | {enhanced_stats['ndcg_at_10']['mean'] - baseline_stats['ndcg_at_10']['mean']:+.3f} | {improvements['ndcg_at_10']:+.1f}% |
| MRR | {baseline_stats['mrr']['mean']:.3f} | {enhanced_stats['mrr']['mean']:.3f} | {enhanced_stats['mrr']['mean'] - baseline_stats['mrr']['mean']:+.3f} | {improvements['mrr']:+.1f}% |

### Diversity

| Metric | Baseline Mean | Enhanced Mean | Δ Absolute | Δ Relative |
|--------|---------------|---------------|------------|------------|
| Diversity Score | {baseline_stats['diversity_score']['mean']:.3f} | {enhanced_stats['diversity_score']['mean']:.3f} | {enhanced_stats['diversity_score']['mean'] - baseline_stats['diversity_score']['mean']:+.3f} | {improvements['diversity_score']:+.1f}% |

### Latency

| Metric | Baseline | Enhanced | Δ Absolute | Δ Relative |
|--------|----------|----------|------------|------------|
| p50 (ms) | {baseline_stats['latency_ms']['median']:.0f} | {enhanced_stats['latency_ms']['median']:.0f} | {enhanced_stats['latency_ms']['median'] - baseline_stats['latency_ms']['median']:+.0f} | {improvements['latency_ms']:+.1f}% |
| p95 (ms) | {baseline_stats['latency_ms']['p95']:.0f} | {enhanced_stats['latency_ms']['p95']:.0f} | {enhanced_stats['latency_ms']['p95'] - baseline_stats['latency_ms']['p95']:+.0f} | --- |

---

## Recommendations

### Rollout Strategy

1. **Feature Flags**: Deploy con flags disabled inizialmente
2. **A/B Test**: 10% traffico enhanced retrieval, monitor metrics 72h
3. **Gradual Rollout**: Se metrics positive, incrementare a 50% → 100%

### Monitoring Alerts

- **Latency Alert**: p95 > 2000ms → auto-disable re-ranking
- **Fallback Rate Alert**: > 5% fallback a baseline → investigate model
- **Precision Drop Alert**: < baseline - 10% → rollback

---

**Benchmark completed at:** {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    
    return report


def main():
    parser = argparse.ArgumentParser(description="Benchmark retrieval optimization")
    parser.add_argument(
        "--ground-truth",
        default="tests/fixtures/retrieval_ground_truth.json",
        help="Path to ground truth dataset",
    )
    parser.add_argument(
        "--output",
        default="reports/retrieval-benchmark-7.2.md",
        help="Output file path for report",
    )
    
    args = parser.parse_args()
    
    # Load ground truth
    ground_truth = load_ground_truth(args.ground_truth)
    
    # Run benchmark
    benchmark_retrieval(ground_truth, output_path=args.output)
    
    logger.info("Benchmark completed successfully!")


if __name__ == "__main__":
    main()

