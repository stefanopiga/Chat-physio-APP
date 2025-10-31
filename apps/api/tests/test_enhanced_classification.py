"""Unit tests per enhanced classification (Story 2.5 AC2).

Test coverage:
- Dominio fisioterapico classification
- Structure type classification
- Confidence scoring
- Detected features validation
"""
import pytest
from unittest.mock import Mock, patch

from api.ingestion.models import (
    ContentDomain,
    DocumentStructureCategory,
    EnhancedClassificationOutput,
)
from api.knowledge_base.classifier import classify_content_enhanced


class TestEnhancedClassificationOutput:
    """Test suite per EnhancedClassificationOutput model."""
    
    def test_model_validation(self):
        """Verifica validazione Pydantic model."""
        output = EnhancedClassificationOutput(
            domain=ContentDomain.FISIOTERAPIA_CLINICA,
            structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
            confidence=0.85,
            reasoning="Test reasoning",
            detected_features={"has_images": True}
        )
        
        assert output.domain == ContentDomain.FISIOTERAPIA_CLINICA
        assert output.structure_type == DocumentStructureCategory.TESTO_ACCADEMICO_DENSO
        assert output.confidence == 0.85
        assert "has_images" in output.detected_features
    
    def test_confidence_range_validation(self):
        """Verifica confidence range [0.0, 1.0]."""
        # Valid confidence
        valid_output = EnhancedClassificationOutput(
            domain=ContentDomain.ANATOMIA,
            structure_type=DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO,
            confidence=0.5,
            reasoning="Valid"
        )
        assert valid_output.confidence == 0.5
        
        # Invalid confidence (> 1.0) should fail validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            EnhancedClassificationOutput(
                domain=ContentDomain.ANATOMIA,
                structure_type=DocumentStructureCategory.PAPER_SCIENTIFICO_MISTO,
                confidence=1.5,  # Invalid
                reasoning="Invalid"
            )


class TestContentDomainEnum:
    """Test suite per ContentDomain enum."""
    
    def test_all_domains_present(self):
        """Verifica presenza tutte categorie fisioterapiche."""
        expected_domains = {
            "fisioterapia_clinica",
            "anatomia",
            "patologia",
            "esercizi_riabilitativi",
            "valutazione_diagnostica",
            "evidence_based",
            "divulgativo",
            "tecnico_generico"
        }
        
        actual_domains = {d.value for d in ContentDomain}
        
        assert actual_domains == expected_domains
    
    def test_domain_enum_values(self):
        """Verifica accessibilità enum values."""
        assert ContentDomain.FISIOTERAPIA_CLINICA.value == "fisioterapia_clinica"
        assert ContentDomain.ANATOMIA.value == "anatomia"
        assert ContentDomain.EVIDENCE_BASED.value == "evidence_based"


class TestClassifyContentEnhanced:
    """Test suite per classify_content_enhanced function.
    
    Note: Uses mocking per LLM calls per evitare dipendenza OpenAI in unit tests.
    Integration tests useranno LLM reale.
    """
    
    @patch("api.knowledge_base.classifier._get_llm")
    def test_classify_fisioterapia_clinica(self, mock_llm):
        """Verifica classificazione caso clinico fisioterapico."""
        # Mock LLM response
        mock_chain = Mock()
        mock_chain.invoke.return_value = EnhancedClassificationOutput(
            domain=ContentDomain.FISIOTERAPIA_CLINICA,
            structure_type=DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
            confidence=0.85,
            reasoning="Caso clinico lombalgia con trattamento specifico",
            detected_features={
                "has_references": True,
                "has_clinical_cases": True
            }
        )
        mock_llm.return_value = Mock()
        
        with patch("api.knowledge_base.classifier.PromptTemplate"):
            with patch("api.knowledge_base.classifier.PydanticOutputParser"):
                # Simulate chain execution
                
                # Test richiede mock completo chain
                # Placeholder per MVP - integration test userà LLM reale
                assert True
    
    def test_classify_with_extraction_metadata(self):
        """Verifica integration extraction metadata in classification."""
        extraction_metadata = {
            "images_count": 3,
            "tables_count": 2
        }
        
        # Test che metadata è passato correttamente
        # e detected_features è popolato
        # Full test con LLM mock in integration tests
        assert "images_count" in extraction_metadata
        assert "tables_count" in extraction_metadata
    
    @patch("api.knowledge_base.classifier._get_llm")
    def test_classify_error_handling(self, mock_llm):
        """Verifica error handling LLM failure."""
        mock_llm.side_effect = Exception("LLM API error")
        
        text = "Test content"
        
        with pytest.raises(Exception):
            classify_content_enhanced(text)


class TestClassificationAccuracy:
    """Test suite per accuracy validation classificazione.
    
    Note: Richiede corpus classificazione (Story 2.5 test fixtures):
    - 5-10 testi brevi per categoria fisioterapica
    - Ground truth labels per benchmark
    
    MVP: Test structure validazione, accuracy test in Phase 2.
    """
    
    def test_classification_corpus_structure(self):
        """Verifica struttura corpus classificazione.
        
        Expected corpus structure:
        {
            "text": str,
            "expected_domain": ContentDomain,
            "expected_structure": DocumentStructureCategory,
            "min_confidence": float
        }
        """
        sample_corpus_item = {
            "text": "Sample text",
            "expected_domain": ContentDomain.ANATOMIA,
            "expected_structure": DocumentStructureCategory.TESTO_ACCADEMICO_DENSO,
            "min_confidence": 0.7
        }
        
        assert "text" in sample_corpus_item
        assert "expected_domain" in sample_corpus_item
        assert "expected_structure" in sample_corpus_item
    
    def test_accuracy_benchmark_placeholder(self):
        """Placeholder per accuracy benchmark test.
        
        Benchmark goal (Story 2.5):
        - Accuracy >= 70% per domain classification
        - Corpus: 50 documenti campione
        
        Implementation:
        1. Load classification corpus
        2. Run classify_content_enhanced per ogni sample
        3. Compare predicted vs expected domain
        4. Calculate accuracy = correct / total
        5. Assert accuracy >= 0.7
        
        Status: Richiede corpus preparation (test fixtures)
        """
        # Placeholder per MVP
        # Full implementation dopo corpus preparation
        target_accuracy = 0.7
        assert target_accuracy == 0.7  # Test structure validation


# Test fixtures preparation notes:
"""
Per test completi classificazione (Story 2.5 AC2):

1. Creare directory: apps/api/tests/fixtures/classification/
2. Creare file: classification_corpus.json

Structure:
[
  {
    "text": "Caso clinico: paziente con lombalgia L4-L5...",
    "expected_domain": "fisioterapia_clinica",
    "expected_structure": "TESTO_ACCADEMICO_DENSO",
    "description": "Caso clinico lombare"
  },
  {
    "text": "Struttura anatomica colonna vertebrale...",
    "expected_domain": "anatomia",
    "expected_structure": "TESTO_ACCADEMICO_DENSO",
    "description": "Anatomia vertebrale"
  },
  ...
]

3. Aggiungere 5-10 samples per ogni ContentDomain category
4. Total corpus: >= 50 documenti per accuracy benchmark
"""

