"""
Dynamic retrieval strategy - adaptive match count based on query complexity.

Story 7.2 AC2: Match count heuristics per ottimizzare retrieval.

Strategy:
- Query semplici (definitional, <6 parole): 5 chunk
- Query normali: 8 chunk (default)
- Query complesse (comparative, >12 parole): 12 chunk

Heuristics:
- Word count analysis
- Complexity keywords detection ("confronta", "differenza", "vs")
- Entity count estimation (nomi anatomici, tecniche)
- Question type assessment (definitional vs comparative)
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from ..config import Settings, get_settings

logger = logging.getLogger("api")

# Complexity keywords (comparative, explanatory queries)
COMPLEX_KEYWORDS = {
    "confronta", "confrontare", "differenza", "differenze",
    "vs", "versus", "oppure", "invece",
    "quali sono", "quali differenze", "come si distingue",
    "meglio", "peggio", "vantaggi", "svantaggi",
    "quando usare", "quando applicare",
    "rispetto a", "in confronto",
    "diverso", "diversa", "diversi", "diverse",
}

# Simple keywords (definitional queries)
SIMPLE_KEYWORDS = {
    "cos'è", "cos è", "cosa è", "cosa e",
    "definizione", "definisci", "spiega",
    "che cos'è", "che cosa è",
}

# Medical/anatomical entity patterns (indicatori complessità)
ENTITY_PATTERNS = [
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b",  # CamelCase entities (es: Legamento Crociato)
    r"\b(?:muscolo|legamento|tendine|articolazione|vertebra)\s+\w+",
    r"\b(?:test|manovra|tecnica)\s+di\s+\w+",
]


class DynamicRetrievalStrategy:
    """
    Dynamic match count strategy basato su query complexity.
    
    Story 7.2 AC2: Adaptive retrieval per efficienza e completeness.
    
    Usage:
        strategy = DynamicRetrievalStrategy(settings)
        match_count = strategy.get_optimal_match_count("dolore lombare cronico")
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize strategy.
        
        Args:
            settings: Application settings (default: get_settings())
        """
        self.settings = settings or get_settings()
    
    def get_optimal_match_count(
        self,
        query: str,
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
        default_count: Optional[int] = None,
    ) -> int:
        """
        Calcola optimal match count basato su query complexity.
        
        Story 7.2 AC2: Heuristic algorithm per adaptive retrieval.
        
        Algorithm:
        1. Assess query type (simple vs complex)
        2. Count words e entities
        3. Detect complexity keywords
        4. Return match count in range [min, max]
        
        Args:
            query: User query string
            min_count: Minimum match count (default: settings.dynamic_match_count_min)
            max_count: Maximum match count (default: settings.dynamic_match_count_max)
            default_count: Default match count (default: settings.dynamic_match_count_default)
            
        Returns:
            Optimal match count (int in [min, max])
        """
        if not query or not query.strip():
            return default_count or self.settings.dynamic_match_count_default
        
        min_count = min_count or self.settings.dynamic_match_count_min
        max_count = max_count or self.settings.dynamic_match_count_max
        default_count = default_count or self.settings.dynamic_match_count_default
        
        query_lower = query.lower().strip()
        
        # Heuristic 1: Simple query detection (definitional)
        if self._is_simple_query(query_lower):
            computed_count = min_count
            logger.info({
                "event": "dynamic_match_count_computed",
                "query_preview": query[:100],
                "query_type": "simple_definitional",
                "computed_count": computed_count,
                "reason": "simple_keywords_detected",
            })
            return computed_count
        
        # Heuristic 2: Complex query detection (comparative, explanatory)
        if self._is_complex_query(query_lower):
            computed_count = max_count
            logger.info({
                "event": "dynamic_match_count_computed",
                "query_preview": query[:100],
                "query_type": "complex_comparative",
                "computed_count": computed_count,
                "reason": "complex_keywords_detected",
            })
            return computed_count
        
        # Heuristic 3: Word count analysis
        word_count = len(query_lower.split())
        if word_count < 6:
            # Short query → simple
            computed_count = min_count
            reason = f"word_count_{word_count}_lt_6"
        elif word_count > 12:
            # Long query → complex
            computed_count = max_count
            reason = f"word_count_{word_count}_gt_12"
        else:
            # Normal query → default
            computed_count = default_count
            reason = f"word_count_{word_count}_normal"
        
        # Heuristic 4: Entity count adjustment (+1 chunk per entity oltre 1)
        entity_count = self._estimate_entity_count(query)
        if entity_count > 1:
            adjustment = min(entity_count - 1, 2)  # Max +2 chunk per entities
            computed_count = min(computed_count + adjustment, max_count)
            reason += f"_entities_{entity_count}_adj_{adjustment}"
        
        logger.info({
            "event": "dynamic_match_count_computed",
            "query_preview": query[:100],
            "query_type": "normal",
            "word_count": word_count,
            "entity_count": entity_count,
            "computed_count": computed_count,
            "reason": reason,
        })
        
        return computed_count
    
    def _is_simple_query(self, query_lower: str) -> bool:
        """
        Detect simple/definitional queries.
        
        Args:
            query_lower: Lowercased query
            
        Returns:
            True if simple query
        """
        for keyword in SIMPLE_KEYWORDS:
            if keyword in query_lower:
                return True
        return False
    
    def _is_complex_query(self, query_lower: str) -> bool:
        """
        Detect complex/comparative queries.
        
        Args:
            query_lower: Lowercased query
            
        Returns:
            True if complex query
        """
        for keyword in COMPLEX_KEYWORDS:
            if keyword in query_lower:
                return True
        return False
    
    def _estimate_entity_count(self, query: str) -> int:
        """
        Estimate medical/anatomical entity count in query.
        
        Heuristic: conta pattern entità mediche/anatomiche.
        
        Args:
            query: Original query (case-sensitive)
            
        Returns:
            Estimated entity count (int >= 0)
        """
        entity_count = 0
        for pattern in ENTITY_PATTERNS:
            matches = re.findall(pattern, query)
            entity_count += len(matches)
        
        # Deduplication: se stesso match ripetuto, conta 1
        # (approssimazione veloce senza NER)
        return min(entity_count, 5)  # Cap a 5 per evitare outlier


def get_dynamic_strategy(settings: Optional[Settings] = None) -> DynamicRetrievalStrategy:
    """
    Factory function per DynamicRetrievalStrategy.
    
    Args:
        settings: Application settings (default: get_settings())
        
    Returns:
        DynamicRetrievalStrategy instance
    """
    return DynamicRetrievalStrategy(settings=settings)

