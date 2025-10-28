from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class DocumentStructureCategory(str, Enum):
    TESTO_ACCADEMICO_DENSO = "TESTO_ACCADEMICO_DENSO"
    PAPER_SCIENTIFICO_MISTO = "PAPER_SCIENTIFICO_MISTO"
    DOCUMENTO_TABELLARE = "DOCUMENTO_TABELLARE"


class ContentDomain(str, Enum):
    """Domini di contenuto per classificazione dominio-specifica (Story 2.5).
    
    Categorie definite in collaborazione con esperto di dominio fisioterapico
    sulla base dell'analisi corpus documenti esistente in:
    conoscenza/fisioterapia/{lombare, cervicale, arto_superiore, ginocchio_e_anca, etc.}
    """
    FISIOTERAPIA_CLINICA = "fisioterapia_clinica"  # Casi clinici, trattamenti specifici
    ANATOMIA = "anatomia"  # Strutture anatomiche, biomeccanica
    PATOLOGIA = "patologia"  # Descrizioni patologie muscoloscheletriche
    ESERCIZI_RIABILITATIVI = "esercizi_riabilitativi"  # Protocolli esercizi terapeutici
    VALUTAZIONE_DIAGNOSTICA = "valutazione_diagnostica"  # Test clinici, assessment
    EVIDENCE_BASED = "evidence_based"  # Paper scientifici, RCT, revisioni sistematiche
    DIVULGATIVO = "divulgativo"  # Materiale educativo per pazienti
    TECNICO_GENERICO = "tecnico_generico"  # Altro contenuto tecnico


class ClassificazioneOutput(BaseModel):
    classificazione: DocumentStructureCategory
    motivazione: str = Field(min_length=3)
    confidenza: float

    @field_validator("confidenza")
    @classmethod
    def validate_confidenza(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("confidenza deve essere nel range [0.0, 1.0]")
        return v


class EnhancedClassificationOutput(BaseModel):
    """Enhanced classification con dominio + struttura (Story 2.5 AC2).
    
    Extends ClassificazioneOutput con:
    - domain: Dominio contenuto fisioterapico
    - structure_type: Tipo struttura documento (da Story 2.2)
    - detected_features: Features rilevate (immagini, tabelle, etc.)
    """
    domain: ContentDomain
    structure_type: DocumentStructureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=3)
    detected_features: Dict[str, bool] = Field(default_factory=dict)


class Document(BaseModel):
    file_name: str
    file_path: str
    file_hash: str
    status: str
    chunking_strategy: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
