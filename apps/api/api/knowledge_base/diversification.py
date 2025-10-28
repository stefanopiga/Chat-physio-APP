"""
Chunk diversification - anti-ridondanza algorithm.

Story 7.2 AC3: Diversificazione documenti per evitare ridondanza.

Algorithm:
- Max 2 chunk dallo stesso documento in top-k finali
- Preserve top-3 chunk indipendentemente (precision guarantee)
- Maintain relevance order

Metrics:
- Document diversity score: unique documents / total chunks (0.0-1.0)
- Target: 0.40 → 0.67 (+68% improvement)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Dict, List

logger = logging.getLogger("api")


def diversify_chunks(
    chunks: List[Dict[str, Any]],
    max_per_doc: int = 2,
    preserve_top_n: int = 3,
) -> List[Dict[str, Any]]:
    """
    Apply chunk diversification: limit max chunks per document.
    
    Story 7.2 AC3: Anti-ridondanza algorithm con precision priority.
    
    Algorithm:
    1. Preserve top-N chunk indipendentemente (precision guarantee)
    2. Per chunk rimanenti: enforce max_per_doc limit
    3. Maintain relevance order (chunks già ordinati per rerank_score)
    
    Args:
        chunks: List of chunks (ordinati per relevance)
        max_per_doc: Maximum chunks from same document (default: 2)
        preserve_top_n: Number of top chunks to preserve (default: 3)
        
    Returns:
        Diversified chunks list
    """
    if not chunks:
        return []
    
    if max_per_doc <= 0:
        logger.warning({
            "event": "diversify_invalid_max_per_doc",
            "max_per_doc": max_per_doc,
            "action": "return_original",
        })
        return chunks
    
    # Track document counts
    doc_counts: Dict[str, int] = defaultdict(int)
    diversified: List[Dict[str, Any]] = []
    
    for idx, chunk in enumerate(chunks):
        doc_id = chunk.get("document_id")
        
        # Preserve top-N sempre (precision priority)
        if idx < preserve_top_n:
            diversified.append(chunk)
            if doc_id:
                doc_counts[doc_id] += 1
            continue
        
        # Apply max_per_doc limit per chunk oltre top-N
        if not doc_id:
            # Nessun document_id: include sempre (edge case)
            diversified.append(chunk)
            continue
        
        if doc_counts[doc_id] < max_per_doc:
            diversified.append(chunk)
            doc_counts[doc_id] += 1
        else:
            # Skip chunk: documento già rappresentato max_per_doc volte
            logger.debug({
                "event": "diversify_chunk_skipped",
                "chunk_id": chunk.get("id"),
                "document_id": doc_id,
                "doc_count": doc_counts[doc_id],
                "max_per_doc": max_per_doc,
            })
    
    logger.info({
        "event": "diversify_completed",
        "input_count": len(chunks),
        "output_count": len(diversified),
        "removed_count": len(chunks) - len(diversified),
        "unique_documents": len(doc_counts),
        "max_per_doc": max_per_doc,
        "preserve_top_n": preserve_top_n,
    })
    
    return diversified


def get_document_distribution(chunks: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calcola distribuzione documenti nei chunk.
    
    Args:
        chunks: List of chunks
        
    Returns:
        Dict mapping document_id → count
    """
    distribution: Dict[str, int] = defaultdict(int)
    
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if doc_id:
            distribution[doc_id] += 1
    
    return dict(distribution)


def calculate_diversity_score(chunks: List[Dict[str, Any]]) -> float:
    """
    Calcola document diversity score: unique documents / total chunks.
    
    Story 7.2 AC3: Metric 0.0-1.0 per diversity tracking.
    
    Interpretation:
    - 0.0: Tutti chunk da stesso documento (worst)
    - 1.0: Ogni chunk da documento diverso (best)
    - Target: 0.40 → 0.67 (+68% improvement)
    
    Args:
        chunks: List of chunks
        
    Returns:
        Diversity score (float 0.0-1.0)
    """
    if not chunks:
        return 0.0
    
    unique_docs = set()
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        if doc_id:
            unique_docs.add(doc_id)
    
    # Edge case: nessun document_id → assume diversity 1.0 (non penalizziamo)
    if not unique_docs:
        return 1.0
    
    diversity_score = len(unique_docs) / len(chunks)
    return diversity_score

