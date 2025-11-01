# Epic 6: Documentation & Pipeline Consolidation

**Priority:** CRITICAL  
**Status:** Planned  
**Owner:** Architecture Team & Documentation Team

## Epic Goal

Risolvere discrepanze critiche tra documentazione e codice sorgente nella pipeline di ingestion, consolidare le due pipeline esistenti (watcher automatica e API manuale), e garantire accuratezza della documentazione tecnica.

## Background

Un'analisi di allineamento approfondita ha rivelato discrepanze significative tra la documentazione architetturale e l'implementazione effettiva del sistema di ingestion:

### Problemi Critici Identificati

1. **Due Pipeline Non Documentate**: 
   - Esistono due pipeline completamente separate (watcher automatica e API manuale)
   - La documentazione descrive solo la pipeline API sofisticata
   - Gli utenti/sviluppatori non sono consapevoli delle differenze

2. **Feature Mismatch**:
   - **Pipeline Watcher** (automatica): usa LangChain basic, NO classificazione LLM, NO PyMuPDF
   - **Pipeline API** (manuale): usa PyMuPDF, classificazione LLM, chunking intelligente
   - Documentazione implica che tutte le feature siano sempre attive

3. **Impatto Operativo**:
   - Documenti processati via watcher non beneficiano di chunking ottimale
   - Classificazione LLM ignorata nella pipeline automatica
   - Metadata immagini/tabelle non estratti in modalità automatica

4. **Debito Documentale**:
   - Separatori LangChain documentati in modo impreciso
   - Note di implementazione ("Phase 2") non chiare
   - Benchmark riferiti solo alla pipeline API

## Epic Value Proposition

**Per gli sviluppatori:**
- Comprensione chiara delle due pipeline e quando usarle
- Documentazione accurata che riflette il codice reale
- Riduzione confusione e debugging time

**Per il sistema:**
- Pipeline watcher potenziata con classificazione intelligente
- Qualità chunking uniforme tra modalità automatica e manuale
- Estrazione metadata coerente

**Per la manutenibilità:**
- Sincronizzazione documentazione-codice
- Feature flags per controllo granulare delle capabilities
- Base solida per future evoluzioni

## Stories

### 6.1: Pipeline Documentation & Watcher Enhancement (CRITICAL)

**Goal:** Documentare le due pipeline e integrare classificazione LLM nella pipeline watcher

**Acceptance Criteria:**
1. Documentazione chiara delle due pipeline (watcher vs API) con use case
2. Pipeline watcher integrata con DocumentExtractor (PyMuPDF)
3. Classificazione LLM abilitata in pipeline watcher con feature flag
4. Metadata immagini/tabelle estratti in entrambe le pipeline
5. Test coverage per pipeline watcher enhanced
6. Documentazione architetturale aggiornata

**Estimated Effort:** 2-3 giorni

---

### 6.2: Documentation Corrections & Cleanup (MEDIUM)

**Goal:** Correggere imprecisioni nella documentazione e aggiungere note di implementazione

**Acceptance Criteria:**
1. Separatori LangChain documentati correttamente
2. Note di implementazione aggiunte al benchmark document
3. Riferimenti "Phase 2" chiariti o rimossi
4. Addendum con stato attuale delle feature (MVP vs future)
5. Documentazione codice sorgente allineata con architettura

**Estimated Effort:** 1 giorno

## Technical Dependencies

- **LangChain**: RecursiveCharacterTextSplitter, PyPDFLoader, Docx2txtLoader
- **PyMuPDF (fitz)**: Extraction avanzata PDF con immagini/tabelle
- **OpenAI**: Classificazione LLM enhanced
- **Redis**: Classification cache (opzionale)
- **Supabase**: Vector store, document storage

## Success Metrics

1. **Documentazione-Codice Alignment:** >95% (da 65% attuale)
2. **Pipeline Watcher Quality:** Classificazione attiva per >80% documenti
3. **Developer Clarity:** Zero ambiguità su pipeline capabilities
4. **Test Coverage:** >85% per codice modificato

## Risks & Mitigations

### Risk 1: Regressione Pipeline Watcher
- **Mitigazione:** Feature flag per abilitate gradualmente, test approfonditi

### Risk 2: Performance Impact (Classificazione LLM)
- **Mitigazione:** Cache Redis, batch processing, timeout configurabili

### Risk 3: Costi OpenAI Aumentati
- **Mitigazione:** Cache hit rate monitoring, budget alerts

## Definition of Done

- [ ] Entrambe le storie (6.1, 6.2) completate e in produzione
- [ ] Documentazione architetturale completa e accurata
- [ ] Pipeline watcher produce chunk quality equivalente a pipeline API
- [ ] Test suite verde (>85% coverage)
- [ ] Peer review completato con approvazione Architecture team
- [ ] Monitoring metriche attivo per classificazione e caching

## Related Documentation

- `docs/architecture/addendum-chunking-strategy-benchmark.md`
- `docs/architecture/addendum-langchain-loaders-splitters.md`
- `docs/architecture/addendum-enhanced-document-extraction.md`
- `apps/api/api/ingestion/watcher.py`
- `apps/api/api/routers/knowledge_base.py`
- `apps/api/api/knowledge_base/extractors.py`
- `apps/api/api/knowledge_base/classifier.py`

---

**Created:** 2025-01-17  
**Last Updated:** 2025-01-17  
**Version:** 1.0

