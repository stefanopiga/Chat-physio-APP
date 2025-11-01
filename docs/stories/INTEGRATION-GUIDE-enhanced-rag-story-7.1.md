# Story 7.1: Enhanced Academic RAG - Integration Guide

**Document Type**: Integration Guide  
**Date**: 2025-10-22  
**Status**: Draft  
**Story ID**: 7.1

---

## Overview

Documentazione modulare completa per implementazione sistema RAG accademico-medico propedeutico con memoria conversazionale e retrieval ottimizzato.

**Obiettivo**: Trasformare chat RAG da Q&A stateless a tutor medico accademico interattivo.

---

## Documentazione Creata

### 1. Analisi Generale

**File**: `docs/architecture/addendum-rag-enhancement-analysis.md`

**Contenuto**:
- Analisi gap sistema attuale vs target
- 4 aree di enhancement: tono, modelli, retrieval, memoria
- Modalità d'uso (domande mirate vs esplorative)
- Raccomandazioni prioritizzate
- Validation plan

**Target audience**: Product Owner, Tech Lead, Backend Team

---

### 2. Cross-Encoder Re-ranking

#### 2.1 Architettura e Implementazione
**File**: `docs/architecture/addendum-cross-encoder-reranking-patterns.md`

**Contenuto**:
- Bi-encoder vs cross-encoder comparison
- Pipeline completa: over-retrieve → re-rank → diversify
- `EnhancedChunkRetriever` class implementation
- Performance characteristics (+26% precision, +500ms latency)
- Best practices (lazy loading, batch prediction)
- Error handling e monitoring

**Dependencies**: `sentence-transformers ^2.2.2`

#### 2.2 Quick Reference
**File**: `docs/architecture/addendum-cross-encoder-quick-reference.md`

**Contenuto**:
- Installation one-liner
- Basic usage examples
- Model comparison table
- Common patterns (re-rank, top-k, threshold)
- Performance tips
- Score interpretation guide

**Target audience**: Developer implementando retrieval

#### 2.3 Testing Guide
**File**: `docs/architecture/addendum-cross-encoder-testing-guide.md`

**Contenuto**:
- Unit tests (lazy loading, diversification, threshold)
- Integration tests (E2E con modello reale)
- Benchmark tests (precision@k measurement)
- Latency validation
- Ground truth dataset creation
- Monitoring in production

**Target audience**: QA, Backend Developer

---

### 3. Memoria Conversazionale

**File**: `docs/architecture/addendum-conversational-memory-patterns.md`

**Contenuto**:
- Context window structure (ultimi 3 turni)
- Pydantic models: `ConversationMessage`, `ChatContextWindow`
- `ConversationManager` service implementation
- Token budget management (2000 token limit)
- Integration con RAG endpoint
- Use cases (follow-up, approfondimenti, correzioni)
- Testing strategies

**Dependencies**: `tiktoken ^0.5.1`

---

### 4. Modelli Pydantic Arricchiti

**File**: `docs/architecture/addendum-structured-academic-responses.md`

**Contenuto**:
- `EnhancedAcademicResponse` model (7 campi strutturati)
- `CitationMetadata` model (metadata completi fonte)
- Validazioni Pydantic
- LLM prompt per structured output
- Frontend integration examples (React components)
- Analytics & monitoring
- Migration strategy con feature flag

---

### 5. Prompt Accademico-Medico

**File**: `docs/architecture/addendum-academic-medical-prompting.md`

**Contenuto**:
- Target persona: medico fisioterapista accademico
- Enhanced prompt template con struttura propedeutica
- Conversational memory integration
- Mode-specific instructions (focused/exploratory)
- Before/After examples comparativi
- Best practices (few-shot, constraint reinforcement)
- Testing effectiveness
- Common pitfalls & solutions

---

### 6. Dynamic Retrieval Strategies

**File**: `docs/architecture/addendum-dynamic-retrieval-strategies.md`

**Contenuto**:
- Query complexity analysis (5 tipologie)
- Heuristic algorithm per match_count dinamico (5-12 chunk)
- `DynamicRetrievalStrategy` implementation
- Examples per ogni tipologia query
- Performance impact (+10% latency reduction, +12% completeness)
- ML-based strategy (Phase 2)
- Configuration e monitoring

---

### 7. Chunk Diversification

**File**: `docs/architecture/addendum-chunk-diversification-patterns.md`

**Contenuto**:
- Problem: ridondanza chunk stesso documento
- `diversify_chunks` algorithm (max 2/doc, preserve top-3)
- Trade-offs precision vs diversity
- Examples con distribuzione before/after
- Advanced: content-based diversification (Phase 2)
- Monitoring diversity score
- Testing strategies

---

### 8. A/B Testing Framework

**File**: `docs/qa/methodologies/rag-ab-testing-framework.md`

**Contenuto**:
- Experiment design methodology
- Hypothesis definition template
- Sample size calculation (Python implementation)
- Randomization strategy (user-level)
- Metrics definition (primary, secondary, guardrails)
- Statistical testing (two-proportion, t-test)
- Backend infrastructure (variant assignment, execution)
- Analysis workflow (daily monitoring, final report)
- Decision framework (launch criteria)
- Example completo con risultati

---

## Implementation Tasks per Story 7.1

### Task 1: Prompt Accademico (2-3h)
**References**:
- `addendum-academic-medical-prompting.md`
- `addendum-rag-enhancement-analysis.md` §1

**Steps**:
1. Implementare `ACADEMIC_MEDICAL_SYSTEM_PROMPT` template
2. Aggiornare `ChatPromptTemplate` in `chat.py`
3. A/B test: baseline vs nuovo prompt (sample 20 query)

**Files modified**:
- `apps/api/api/routers/chat.py`
- `apps/api/api/prompts/academic_medical.py` (new)

---

### Task 2: Enhanced Pydantic Models (2h)
**References**:
- `addendum-structured-academic-responses.md`
- `addendum-rag-enhancement-analysis.md` §2

**Steps**:
1. Creare `apps/api/api/models/enhanced_response.py`
2. Implementare `EnhancedAcademicResponse` + `CitationMetadata`
3. Migration parser da `AnswerWithCitations`

**Files modified**:
- `apps/api/api/models/enhanced_response.py` (new)
- `apps/api/api/routers/chat.py` (parser update)

**Dependencies**: None (Pydantic già presente)

---

### Task 3: Retrieval Optimization (5h)
**References**:
- `addendum-cross-encoder-reranking-patterns.md`
- `addendum-cross-encoder-quick-reference.md`
- `addendum-dynamic-retrieval-strategies.md`
- `addendum-chunk-diversification-patterns.md`

**Steps**:
1. Install `sentence-transformers@^2.2.2`
2. Implementare `EnhancedChunkRetriever` con re-ranking
3. Implementare `DynamicRetrievalStrategy`
4. Implementare `diversify_chunks`
5. Integration endpoint chat
6. Benchmark precision improvement

**Files modified**:
- `apps/api/pyproject.toml` (dependencies)
- `apps/api/api/knowledge_base/enhanced_retrieval.py` (new)
- `apps/api/api/knowledge_base/dynamic_retrieval.py` (new)
- `apps/api/api/knowledge_base/diversification.py` (new)
- `apps/api/api/routers/chat.py` (use enhanced retrieval)

**Dependencies**: 
```toml
[tool.poetry.dependencies]
sentence-transformers = "^2.2.2"
```

---

### Task 4: Conversational Memory (4h)
**References**:
- `addendum-conversational-memory-patterns.md`
- `addendum-rag-enhancement-analysis.md` §4

**Steps**:
1. Ensure `tiktoken` esplicito in dependencies
2. Implementare `ConversationManager` service
3. Integrare context window in prompt generation
4. Add persistence turni conversazionali a store
5. API `GET /chat/sessions/{sessionId}/history` per debug

**Files modified**:
- `apps/api/pyproject.toml` (tiktoken esplicito)
- `apps/api/api/services/conversation_service.py` (new)
- `apps/api/api/models/conversation.py` (new)
- `apps/api/api/routers/chat.py` (integration)

**Dependencies**:
```toml
[tool.poetry.dependencies]
tiktoken = "^0.5.1"  # Render esplicito
```

---

### Task 5: Conversation Modes (2h) [Optional]
**References**:
- `addendum-academic-medical-prompting.md` (mode-specific)
- `addendum-rag-enhancement-analysis.md` §5

**Steps**:
1. Add `conversation_mode` field to `ChatRequest` schema
2. Implement mode-specific instructions injection
3. Auto-detect mode da query (opzionale)

**Files modified**:
- `apps/api/api/schemas/chat.py`
- `apps/api/api/routers/chat.py`

---

### Task 6: Testing & Validation (3h)
**References**:
- `addendum-cross-encoder-testing-guide.md`
- `docs/qa/methodologies/rag-ab-testing-framework.md`

**Steps**:
1. Unit tests per ogni nuovo component
2. Integration test conversational follow-up
3. Benchmark retrieval precision@k
4. Setup A/B test infrastructure
5. Launch 2-week A/B test

**Files modified**:
- `apps/api/tests/knowledge_base/test_enhanced_retrieval.py` (new)
- `apps/api/tests/services/test_conversation_service.py` (new)
- `apps/api/tests/models/test_enhanced_response.py` (new)
- `apps/api/api/services/ab_testing.py` (new)

---

### Task 7: Documentation & Config (2h)
**References**: Tutti i documenti

**Steps**:
1. Update `docs/architecture/sezione-4-modelli-di-dati.md` con nuovi models
2. User guide: "Come usare chat per studiare"
3. Update config.py con feature flags

**Files modified**:
- `apps/api/api/config.py`
- `docs/architecture/sezione-4-modelli-di-dati.md`
- `docs/user-guides/chat-study-guide.md` (new)

---

## Effort Summary

| Task | Hours | Priority | Dependencies |
|------|-------|----------|--------------|
| T1: Prompt | 2-3h | ⭐⭐⭐ Must-Have | None |
| T2: Models | 2h | ⭐⭐⭐ Must-Have | None |
| T3: Retrieval | 5h | ⭐⭐ Should-Have | sentence-transformers |
| T4: Memory | 4h | ⭐⭐⭐ Must-Have | tiktoken |
| T5: Modes | 2h | ⭐ Could-Have | T1, T4 |
| T6: Testing | 3h | ⭐⭐⭐ Must-Have | T1-T4 |
| T7: Docs | 2h | ⭐⭐ Should-Have | All |
| **Total** | **20-21h** | | |

**Sprint allocation**: 2 sprints (10-11h per sprint)

---

## Dependencies to Add

### pyproject.toml

```toml
[tool.poetry.dependencies]
# ... existing ...
sentence-transformers = "^2.2.2"  # Cross-encoder re-ranking
tiktoken = "^0.5.1"  # Token counting per conversational memory
```

### Installation

```bash
cd apps/api
poetry add sentence-transformers@^2.2.2
poetry add tiktoken@^0.5.1
```

**Note**: `torch` (500MB+) è transitive dependency di sentence-transformers. Verificare se già presente.

---

## Feature Flags

### Configuration

```python
# apps/api/api/config.py

class Settings(BaseSettings):
    # ... existing ...
    
    # Story 7.1 feature flags
    enable_enhanced_response_model: bool = Field(default=False, env="ENABLE_ENHANCED_RESPONSE_MODEL")
    enable_cross_encoder_reranking: bool = Field(default=False, env="ENABLE_CROSS_ENCODER_RERANKING")
    enable_conversational_memory: bool = Field(default=False, env="ENABLE_CONVERSATIONAL_MEMORY")
    enable_dynamic_match_count: bool = Field(default=False, env="ENABLE_DYNAMIC_MATCH_COUNT")
    enable_chunk_diversification: bool = Field(default=False, env="ENABLE_CHUNK_DIVERSIFICATION")
```

### Rollout Strategy

**Phase 1: MVP** (settimana 1-2)
```
ENABLE_ENHANCED_RESPONSE_MODEL=false  # Implement ma non attivare
ENABLE_CROSS_ENCODER_RERANKING=false  # Implement ma non attivare
ENABLE_CONVERSATIONAL_MEMORY=true     # ✅ Attivare subito (core value)
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false
```

**Phase 2: A/B Test** (settimana 3-4)
```
# 50% utenti con enhanced features
if ab_test_variant == "treatment":
    ENABLE_ENHANCED_RESPONSE_MODEL=true
    ENABLE_CROSS_ENCODER_RERANKING=true
    ENABLE_DYNAMIC_MATCH_COUNT=true
    ENABLE_CHUNK_DIVERSIFICATION=true
```

**Phase 3: Full Rollout** (settimana 5+)
```
# Se A/B test positivo, enable per tutti
ALL_FLAGS=true
```

---

## Success Metrics (from A/B Test Framework)

### Primary
- **User Satisfaction**: 62% → 75% (+13pp target)
- **Precision@5**: 0.65 → 0.82 (+26%)

### Secondary
- **Messages/session**: 1.2 → 2.5 (+108%)
- **Follow-up rate**: 18% → 45% (+27pp)
- **Session duration**: 2.1min → 4.0min (+90%)

### Guardrails
- **Latency p95**: < 3000ms (retrieval + generation)
- **Error rate**: < 2%

---

## Risk Mitigation

### R1: Cross-Encoder Latency
- **Mitigation**: Lazy loading, batch scoring, threshold skip se latency > 1s
- **Monitoring**: `rerank_latency_p95_ms` metric

### R2: Token Overflow (Conversational Memory)
- **Mitigation**: Hard limit 2000 token, truncate oldest messages
- **Monitoring**: `context_window_tokens` per session

### R3: Structured Output Parsing Failures
- **Mitigation**: Fallback a `StrOutputParser`, wrap in minimal structure
- **Monitoring**: `parsing_failure_rate` metric

---

## Next Steps (Post-Implementation)

1. **Week 1-2**: Implement MVP (Tasks 1,2,4)
2. **Week 3**: Implement retrieval optimization (Task 3)
3. **Week 4**: Testing e A/B test setup (Task 6)
4. **Week 5-6**: A/B test running
5. **Week 7**: Analysis, decision, rollout

---

## Questions for Product Owner

1. **Priorità Task 3 (Retrieval Optimization)**: Must-Have o Could-Have?
   - Pro: +26% precision improvement
   - Con: +500ms latency, nuova dependency (sentence-transformers)

2. **A/B Test Duration**: 2 settimane sufficienti? (dipende da traffic)

3. **Conversation Modes (Task 5)**: Implementare o defer Phase 2?

4. **Ground Truth Dataset**: Chi fa annotation (docenti)? Budget tempo?

---

**Document Owner**: Scrum Master  
**Reviewers**: Tech Lead, Product Owner  
**Approval Required Before**: Task assignment  
**Last Updated**: 2025-10-22

