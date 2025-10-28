"""
Unit tests for dynamic retrieval strategy.

Story 7.2 AC2: Test match count heuristics.
"""
import pytest
from unittest.mock import Mock

from api.knowledge_base.dynamic_retrieval import (
    DynamicRetrievalStrategy,
    get_dynamic_strategy,
    COMPLEX_KEYWORDS,
    SIMPLE_KEYWORDS,
)
from api.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock(spec=Settings)
    settings.dynamic_match_count_min = 5
    settings.dynamic_match_count_max = 12
    settings.dynamic_match_count_default = 8
    return settings


class TestDynamicRetrievalStrategy:
    """Test DynamicRetrievalStrategy class."""
    
    def test_init(self, mock_settings):
        """Test strategy initialization."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        assert strategy.settings == mock_settings
    
    def test_simple_query_definitional(self, mock_settings):
        """Test che query semplici definitional ritornino min count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        simple_queries = [
            "cos'è il dolore lombare",
            "definizione di scoliosi",
            "che cos'è la cifosi",
            "spiega la lordosi",
        ]
        
        for query in simple_queries:
            count = strategy.get_optimal_match_count(query)
            assert count == 5, f"Query '{query}' dovrebbe ritornare min_count (5)"
    
    def test_complex_query_comparative(self, mock_settings):
        """Test che query complesse comparative ritornino max count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        complex_queries = [
            "confronta lordosi e cifosi",
            "differenza tra scoliosi e cifosi",
            "quali sono i vantaggi del metodo McKenzie vs Williams",
            "quando usare manipolazione oppure mobilizzazione",
            "dolore lombare acuto rispetto a cronico come si distingue",
        ]
        
        for query in complex_queries:
            count = strategy.get_optimal_match_count(query)
            assert count == 12, f"Query '{query}' dovrebbe ritornare max_count (12)"
    
    def test_normal_query_default_count(self, mock_settings):
        """Test che query normali ritornino default count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        normal_queries = [
            "trattamento dolore lombare cronico persistente",  # 5 parole (6-12 range)
            "esercizi terapeutici per la scoliosi posturale",  # 6 parole
            "terapia manuale colonna vertebrale lombare dorsale",  # 6 parole
        ]
        
        for query in normal_queries:
            count = strategy.get_optimal_match_count(query)
            assert count == 8, f"Query '{query}' dovrebbe ritornare default_count (8)"
    
    def test_short_query_word_count(self, mock_settings):
        """Test che query corte (<6 parole) ritornino min count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        short_queries = [
            "dolore lombare",
            "scoliosi trattamento",
            "cifosi",
            "test di Lasègue",
        ]
        
        for query in short_queries:
            count = strategy.get_optimal_match_count(query)
            assert count == 5, f"Query corta '{query}' dovrebbe ritornare min_count (5)"
    
    def test_long_query_word_count(self, mock_settings):
        """Test che query lunghe (>12 parole) ritornino max count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        long_query = (
            "quali sono le indicazioni e controindicazioni per il trattamento "
            "manipolativo della colonna lombare in pazienti con ernia discale"
        )
        
        count = strategy.get_optimal_match_count(long_query)
        assert count == 12, "Query lunga dovrebbe ritornare max_count (12)"
    
    def test_entity_count_adjustment(self, mock_settings):
        """Test che entity count aumenti match count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        # Query con multiple entità anatomiche
        query_with_entities = "Legamento Crociato Anteriore test Lachman manovra cassetto"
        count = strategy.get_optimal_match_count(query_with_entities)
        
        # Dovrebbe essere > default per entities
        assert count >= 8, "Query con entities dovrebbe avere adjustment positivo"
    
    def test_bounds_respect_min(self, mock_settings):
        """Test che count rispetti lower bound."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        # Override bounds
        count = strategy.get_optimal_match_count(
            "test",
            min_count=10,
            max_count=15,
            default_count=12,
        )
        
        assert count >= 10, "Count deve rispettare min_count"
    
    def test_bounds_respect_max(self, mock_settings):
        """Test che count rispetti upper bound."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        # Query molto complessa che potrebbe eccedere max
        long_query = " ".join(["parola"] * 20)  # 20 parole
        
        count = strategy.get_optimal_match_count(
            long_query,
            min_count=5,
            max_count=10,
        )
        
        assert count <= 10, "Count deve rispettare max_count"
    
    def test_empty_query(self, mock_settings):
        """Test che empty query ritorni default count."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        empty_queries = ["", "   ", None]
        
        for query in empty_queries:
            count = strategy.get_optimal_match_count(query or "")
            assert count == 8, f"Empty query '{query}' dovrebbe ritornare default_count"
    
    def test_is_simple_query(self, mock_settings):
        """Test simple query detection."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        assert strategy._is_simple_query("cos'è la scoliosi")
        assert strategy._is_simple_query("definizione di cifosi")
        assert not strategy._is_simple_query("trattamento scoliosi")
    
    def test_is_complex_query(self, mock_settings):
        """Test complex query detection."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        assert strategy._is_complex_query("confronta lordosi e cifosi")
        assert strategy._is_complex_query("differenza tra scoliosi e cifosi")
        assert strategy._is_complex_query("vantaggi e svantaggi")
        assert not strategy._is_complex_query("trattamento scoliosi")
    
    def test_estimate_entity_count(self, mock_settings):
        """Test entity count estimation."""
        strategy = DynamicRetrievalStrategy(settings=mock_settings)
        
        # Query senza entities
        count_no_entities = strategy._estimate_entity_count("dolore lombare")
        assert count_no_entities >= 0
        
        # Query con entities
        count_with_entities = strategy._estimate_entity_count(
            "Legamento Crociato Anteriore test Lachman"
        )
        assert count_with_entities > 0


def test_get_dynamic_strategy():
    """Test factory function."""
    from unittest.mock import Mock, patch
    
    with patch("api.knowledge_base.dynamic_retrieval.get_settings") as mock_get_settings:
        mock_settings = Mock(spec=Settings)
        mock_get_settings.return_value = mock_settings
        
        strategy = get_dynamic_strategy()
        
        assert isinstance(strategy, DynamicRetrievalStrategy)


def test_complex_keywords_defined():
    """Test che COMPLEX_KEYWORDS sia definito correttamente."""
    assert len(COMPLEX_KEYWORDS) > 0
    assert "confronta" in COMPLEX_KEYWORDS
    assert "differenza" in COMPLEX_KEYWORDS
    assert "vs" in COMPLEX_KEYWORDS


def test_simple_keywords_defined():
    """Test che SIMPLE_KEYWORDS sia definito correttamente."""
    assert len(SIMPLE_KEYWORDS) > 0
    assert "cos'è" in SIMPLE_KEYWORDS or "cos è" in SIMPLE_KEYWORDS
    assert "definizione" in SIMPLE_KEYWORDS

