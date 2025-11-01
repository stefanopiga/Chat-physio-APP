# Structured Academic Response Models

**Document Type**: Data Model Specification  
**Date**: 2025-10-22  
**Status**: Approved  
**Related**: Story 7.1 Task 2

---

## Overview

Modelli Pydantic arricchiti per risposte RAG strutturate in modo pedagogico, sostituendo blob testuale con componenti semantici granulari.

**Migration**: `AnswerWithCitations` (minimal) → `EnhancedAcademicResponse` (structured)

---

## Current State: AnswerWithCitations

**File**: `apps/api/api/models/answer_with_citations.py`

```python
class AnswerWithCitations(BaseModel):
    risposta: str  # Blob testuale non strutturato
    citazioni: List[str]  # Solo ID chunk (stringhe)
```

**Limitazioni**:
- Nessuna struttura pedagogica
- Frontend deve parsing testuale per extract concetti
- Citazioni povere (solo ID, no metadata)
- Impossibile rendering differenziato

---

## Enhanced Models

### EnhancedAcademicResponse

```python
# apps/api/api/models/enhanced_response.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime


class CitationMetadata(BaseModel):
    """
    Metadata completi per citazione fonte con source verification.
    
    Design: Rich citation permette frontend di mostrare popover informativi
    e studente di verificare fonti facilmente.
    """
    
    chunk_id: str = Field(description="UUID chunk primario")
    
    document_id: str = Field(description="UUID documento sorgente")
    
    document_name: str = Field(
        description="Nome file leggibile (es. 'Patologie_Rachide_Lombare.docx')"
    )
    
    page_number: Optional[int] = Field(
        default=None,
        ge=1,
        description="Numero pagina nel documento originale (se disponibile)"
    )
    
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score rilevanza 0-1 (da re-ranking o semantic search)"
    )
    
    excerpt: str = Field(
        max_length=200,
        description="Estratto testuale rilevante per preview (max 200 char)"
    )
    
    content_type: Optional[Literal["theory", "clinical_example", "guideline", "definition", "procedure"]] = Field(
        default=None,
        description="Tipologia contenuto per rendering contestuale"
    )
    
    @validator('excerpt')
    def excerpt_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("excerpt non può essere vuoto")
        return v.strip()


class EnhancedAcademicResponse(BaseModel):
    """
    Risposta strutturata stile medico-accademico propedeutico.
    
    Design principles:
    - Pedagogia esplicita: introduzione → concetti chiave → sviluppo → applicazioni
    - Transparenza: limitazioni contesto esplicitate
    - Self-assessment: confidenza risposta per trasparenza
    - Rich metadata: tutto info necessario per UX frontend ottimale
    """
    
    introduzione: str = Field(
        min_length=20,
        max_length=500,
        description="Contestualizzazione argomento (1-3 frasi)",
        example="La spondilolistesi rappresenta una delle principali patologie strutturali della colonna lombosacrale..."
    )
    
    concetti_chiave: List[str] = Field(
        min_items=2,
        max_items=5,
        description="Concetti essenziali da comprendere (bullet points)",
        example=["Scivolamento vertebrale anteriore", "Classificazione eziologica", "Grading Meyerding"]
    )
    
    spiegazione_dettagliata: str = Field(
        min_length=100,
        description="Core della risposta: spiegazione strutturata e progressiva",
        example="La spondilolistesi è definita come lo scivolamento anteriore di un corpo vertebrale..."
    )
    
    note_cliniche: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Applicazioni pratiche, esempi clinici, o correlazioni cliniche (se presenti nel contesto)"
    )
    
    limitazioni_contesto: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Aspetti non coperti dal materiale disponibile (trasparenza gap conoscenza)"
    )
    
    citazioni: List[CitationMetadata] = Field(
        min_items=1,
        description="Fonti con metadata completi per verifica",
        example=[CitationMetadata(...)]
    )
    
    confidenza_risposta: Literal["alta", "media", "bassa"] = Field(
        description="Autovalutazione completezza risposta basata su materiale disponibile"
    )
    
    metadata: ResponseMetadata = Field(
        default_factory=lambda: ResponseMetadata(),
        description="Metadata tecnici per analytics e debugging"
    )
    
    @validator('concetti_chiave')
    def validate_concepts_not_empty(cls, v):
        if any(not concept.strip() for concept in v):
            raise ValueError("concetti_chiave non possono contenere stringhe vuote")
        return [c.strip() for c in v]
    
    @validator('spiegazione_dettagliata')
    def validate_explanation_substantial(cls, v):
        if len(v.strip()) < 100:
            raise ValueError("spiegazione_dettagliata deve essere sostanziale (>100 char)")
        return v.strip()


class ResponseMetadata(BaseModel):
    """Metadata tecnici per analytics, debugging e monitoring."""
    
    response_id: str = Field(default_factory=lambda: str(uuid4()))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model_name: str = Field(default="gpt-5-nano")
    generation_time_ms: Optional[int] = None
    total_chunks_retrieved: Optional[int] = None
    conversation_turn: Optional[int] = Field(default=None, description="Turno conversazionale (1-based)")
```

---

## LLM Prompt for Structured Output

### PydanticOutputParser Integration

```python
from langchain_core.output_parsers import PydanticOutputParser

# Parser con schema validation
parser = PydanticOutputParser(pydantic_object=EnhancedAcademicResponse)
format_instructions = parser.get_format_instructions()

# Inject format instructions in system prompt
system_prompt = f"""
Sei un medico fisioterapista accademico...

FORMATO OUTPUT:
Restituisci la risposta rispettando esattamente questo schema JSON:
{format_instructions}

CAMPI OBBLIGATORI:
- introduzione: 1-3 frasi contestualizzazione
- concetti_chiave: 2-5 punti essenziali (array stringhe)
- spiegazione_dettagliata: sviluppo completo argomento
- note_cliniche: applicazioni pratiche SE presenti nel materiale (null se assenti)
- limitazioni_contesto: cosa manca nel materiale SE rilevante (null se completo)
- citazioni: array CitationMetadata con tutti i campi
- confidenza_risposta: "alta" | "media" | "bassa"
"""
```

---

## Frontend Integration Examples

### React Components

```typescript
// types/enhanced-response.ts
interface CitationMetadata {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number?: number;
  relevance_score: number;
  excerpt: string;
  content_type?: "theory" | "clinical_example" | "guideline" | "definition" | "procedure";
}

interface EnhancedAcademicResponse {
  introduzione: string;
  concetti_chiave: string[];
  spiegazione_dettagliata: string;
  note_cliniche?: string;
  limitazioni_contesto?: string;
  citazioni: CitationMetadata[];
  confidenza_risposta: "alta" | "media" | "bassa";
  metadata: ResponseMetadata;
}

// components/AcademicResponse.tsx
export function AcademicResponseCard({ response }: { response: EnhancedAcademicResponse }) {
  return (
    <div className="academic-response">
      {/* Introduction */}
      <section className="introduction">
        <p className="text-gray-700 italic">{response.introduzione}</p>
      </section>
      
      {/* Key Concepts - Highlighted */}
      <section className="key-concepts mt-4">
        <h3 className="font-semibold text-lg">📌 Concetti Chiave</h3>
        <ul className="list-disc list-inside space-y-2 mt-2">
          {response.concetti_chiave.map((concept, idx) => (
            <li key={idx} className="font-medium text-blue-900">
              {concept}
            </li>
          ))}
        </ul>
      </section>
      
      {/* Detailed Explanation */}
      <section className="explanation mt-4">
        <h3 className="font-semibold text-lg">Spiegazione Dettagliata</h3>
        <div className="prose mt-2">
          {response.spiegazione_dettagliata}
        </div>
      </section>
      
      {/* Clinical Notes (conditional) */}
      {response.note_cliniche && (
        <section className="clinical-notes mt-4 bg-green-50 p-4 rounded">
          <h3 className="font-semibold text-lg flex items-center">
            🏥 Note Cliniche
          </h3>
          <p className="mt-2">{response.note_cliniche}</p>
        </section>
      )}
      
      {/* Limitations (conditional) */}
      {response.limitazioni_contesto && (
        <section className="limitations mt-4 bg-yellow-50 p-4 rounded border-l-4 border-yellow-400">
          <h3 className="font-semibold text-sm text-yellow-800">
            ⚠️ Limitazioni Materiale Disponibile
          </h3>
          <p className="text-sm text-yellow-700 mt-1">
            {response.limitazioni_contesto}
          </p>
        </section>
      )}
      
      {/* Citations with Rich Popover */}
      <section className="citations mt-6">
        <h3 className="font-semibold text-sm text-gray-600">Fonti</h3>
        <div className="flex flex-wrap gap-2 mt-2">
          {response.citazioni.map((citation, idx) => (
            <CitationBadge key={idx} citation={citation} index={idx + 1} />
          ))}
        </div>
      </section>
      
      {/* Confidence Indicator */}
      <div className="confidence-indicator mt-4 text-xs text-gray-500">
        Confidenza risposta: <ConfidenceBadge level={response.confidenza_risposta} />
      </div>
    </div>
  );
}

// Citation Badge with Popover
function CitationBadge({ citation, index }: { citation: CitationMetadata; index: number }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="citation-badge">
          [{index}] {citation.document_name}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="space-y-2">
          <div className="font-medium">{citation.document_name}</div>
          {citation.page_number && (
            <div className="text-sm text-gray-600">Pagina {citation.page_number}</div>
          )}
          <div className="text-sm bg-gray-50 p-2 rounded italic">
            "{citation.excerpt}"
          </div>
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Rilevanza: {(citation.relevance_score * 100).toFixed(0)}%</span>
            {citation.content_type && (
              <span className="badge">{citation.content_type}</span>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
```

---

## Analytics & Monitoring

### Structured Response Metrics

```python
# Track field usage and quality
logger.info({
    "event": "enhanced_response_generated",
    "response_id": response.metadata.response_id,
    "has_clinical_notes": bool(response.note_cliniche),
    "has_limitations": bool(response.limitazioni_contesto),
    "concepts_count": len(response.concetti_chiave),
    "citations_count": len(response.citazioni),
    "confidenza": response.confidenza_risposta,
    "generation_time_ms": response.metadata.generation_time_ms,
    "explanation_length": len(response.spiegazione_dettagliata)
})

# Aggregate metrics
enhanced_response_metrics = {
    "clinical_notes_rate": Gauge,  # % risposte con note cliniche
    "limitations_disclosure_rate": Gauge,  # % risposte con limitazioni
    "avg_concepts_per_response": Gauge,
    "avg_citations_per_response": Gauge,
    "confidenza_distribution": Counter,  # alta/media/bassa counts
}
```

### A/B Test Metrics

Track differenza engagement baseline vs enhanced:

```python
# Hypothesis: Structured response aumenta engagement
ab_test_metrics = {
    "response_reading_time_ms": Histogram,  # Tempo lettura risposta
    "concept_expansion_clicks": Counter,  # Click su concetti chiave
    "citation_popover_opens": Counter,  # Interazione con citazioni
    "follow_up_rate": Gauge,  # % sessioni con follow-up
}
```

---

## Migration Strategy

### Phase 1: Parallel Implementation

```python
# Feature flag per rollout graduale
class Settings(BaseSettings):
    use_enhanced_response_model: bool = Field(
        default=False,
        env="USE_ENHANCED_RESPONSE_MODEL"
    )

# Conditional parsing in endpoint
if settings.use_enhanced_response_model:
    parser = PydanticOutputParser(pydantic_object=EnhancedAcademicResponse)
    result = enhanced_chain.invoke(...)
else:
    parser = PydanticOutputParser(pydantic_object=AnswerWithCitations)
    result = baseline_chain.invoke(...)
```

### Phase 2: A/B Testing (2 weeks)

- 50/50 split traffic
- Track metrics comparative
- User satisfaction survey

### Phase 3: Full Rollout

- If metrics positive (+10% satisfaction), enable per tutti
- Deprecate AnswerWithCitations
- Remove feature flag

---

## Testing

```python
# tests/models/test_enhanced_response.py

def test_enhanced_response_validation():
    """Test Pydantic validation rules."""
    
    # Valid response
    valid_response = EnhancedAcademicResponse(
        introduzione="Contestualizzazione breve ma sostanziale dell'argomento",
        concetti_chiave=["Concetto 1", "Concetto 2"],
        spiegazione_dettagliata="Spiegazione lunga e dettagliata che supera i 100 caratteri minimi richiesti per validazione",
        citazioni=[
            CitationMetadata(
                chunk_id="123",
                document_id="456",
                document_name="Doc.pdf",
                relevance_score=0.85,
                excerpt="Estratto rilevante"
            )
        ],
        confidenza_risposta="alta"
    )
    assert valid_response
    
    # Invalid: spiegazione troppo corta
    with pytest.raises(ValidationError):
        EnhancedAcademicResponse(
            introduzione="Intro",
            concetti_chiave=["C1"],
            spiegazione_dettagliata="Troppo corta",  # < 100 char
            citazioni=[...],
            confidenza_risposta="alta"
        )
    
    # Invalid: concetti_chiave vuoti
    with pytest.raises(ValidationError):
        EnhancedAcademicResponse(
            introduzione="Intro",
            concetti_chiave=["", "  "],  # Empty strings
            spiegazione_dettagliata="..." * 50,
            citazioni=[...],
            confidenza_risposta="alta"
        )


def test_citation_metadata_validation():
    """Test citation validation."""
    
    # Valid citation
    citation = CitationMetadata(
        chunk_id="123",
        document_id="456",
        document_name="Patologie_Lombare.docx",
        page_number=12,
        relevance_score=0.92,
        excerpt="La spondilolistesi è caratterizzata...",
        content_type="theory"
    )
    assert citation.relevance_score == 0.92
    
    # Invalid: score out of range
    with pytest.raises(ValidationError):
        CitationMetadata(
            ...,
            relevance_score=1.5  # > 1.0
        )
    
    # Invalid: excerpt empty
    with pytest.raises(ValidationError):
        CitationMetadata(
            ...,
            excerpt=""
        )
```

---

## Best Practices

### 1. Prompt Engineering per Structured Output

```python
# Esempi concreti nel prompt aiutano LLM a generare output valido
prompt_with_examples = """
...

ESEMPIO OUTPUT VALIDO:
{{
  "introduzione": "La radicolopatia lombare rappresenta una condizione...",
  "concetti_chiave": [
    "Compressione radice nervosa",
    "Distribuzione dermatomerica dolore",
    "Segni neurologici: ipoestesia, deficit motorio"
  ],
  "spiegazione_dettagliata": "La radicolopatia è definita come...",
  "note_cliniche": "Nel contesto clinico, il paziente tipicamente presenta...",
  "limitazioni_contesto": null,
  "citazioni": [
    {{
      "chunk_id": "abc-123",
      "document_id": "doc-456",
      "document_name": "Radicolopatia_Lombare.docx",
      "page_number": 8,
      "relevance_score": 0.92,
      "excerpt": "La radicolopatia L5-S1 è caratterizzata da...",
      "content_type": "theory"
    }}
  ],
  "confidenza_risposta": "alta"
}}
"""
```

### 2. Fallback Graceful

```python
# Se parsing strutturato fallisce, fallback a testo libero
try:
    result = parser.parse(llm_output)
except Exception as e:
    logger.warning({"event": "structured_parsing_failed", "error": str(e)})
    # Fallback: wrap in minimal structure
    result = EnhancedAcademicResponse(
        introduzione="Risposta generata",
        concetti_chiave=["Vedi spiegazione dettagliata"],
        spiegazione_dettagliata=llm_output,  # Raw text
        citazioni=[...],  # Extract da context
        confidenza_risposta="media"
    )
```

### 3. Frontend Rendering Defensive

```typescript
// Handle optional fields gracefully
{response.note_cliniche ? (
  <ClinicalNotesSection>{response.note_cliniche}</ClinicalNotesSection>
) : null}

// Fallback for missing data
const displayName = citation.document_name || "Documento sconosciuto";
const pageInfo = citation.page_number ? `p. ${citation.page_number}` : "pagina non specificata";
```

---

## References

- Pydantic V2 Docs: https://docs.pydantic.dev/latest/
- LangChain Structured Output: https://python.langchain.com/docs/modules/model_io/output_parsers/types/pydantic/
- JSON Schema Validation: https://json-schema.org/
