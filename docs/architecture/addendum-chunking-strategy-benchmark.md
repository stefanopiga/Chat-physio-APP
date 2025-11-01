# Addendum: Strategia di Chunking - Benchmark e Rationale

**Storia:** 2.11 - Chat RAG End-to-End  
**Requirement:** AC3 - Strategia di Chunking Ottimale Applicata  
**Data:** 2025-10-17  
**Versione:** 1.0

## Executive Summary

La strategia di chunking adottata è **RecursiveCharacterTextSplitter** con parametri:
- `chunk_size`: 800 caratteri
- `chunk_overlap`: 160 caratteri (20%)
- `separators`: default Python (newlines, period+space, spaces)

**Rationale:** Bilanciamento ottimale tra granularità del contesto, qualità del retrieval, e costi operativi per documenti di fisioterapia con struttura paragrafi/sezioni.

## Note Implementazione

> **IMPORTANTE:** I benchmark si riferiscono alla strategia applicata da **entrambe** le pipeline dopo Story 6.1. Prima di questa evoluzione solo la pipeline API manuale utilizzava classificazione intelligente e routing polimorfico. Consulta la guida [Ingestion Pipelines Comparison](ingestion-pipelines-comparison.md) per il dettaglio dei flussi.

## Contesto

### Requisiti di Chunking

1. **Qualità del Contesto**: Chunk devono contenere informazioni semanticamente coerenti per LLM
2. **Efficienza Retrieval**: Chunk devono essere abbastanza specifici per high precision
3. **Recall**: Overlap sufficiente per catturare informazioni a cavallo tra chunk
4. **Costi**: Numero di chunk impatta embedding costs e latenza retrieval
5. **User Experience**: Citazioni devono essere leggibili e pertinenti

### Dataset di Test

- **Documenti**: 11 documenti di fisioterapia (documenti reali della knowledge base)
- **Contenuto**: Anatomia, patologie, trattamenti, procedure cliniche
- **Formato**: Markdown, Word, PDF con struttura paragrafi e sezioni
- **Dimensioni**: Variabile da 2KB a 50KB per documento

## Strategie Valutate

### 1. RecursiveCharacterTextSplitter (800/160) - ADOTTATA

**Configurazione:**
```python
{
    "chunk_size": 800,
    "chunk_overlap": 160,
    "separators": ["\n\n", "\n", ". ", " ", ""]
}
```

**Pro:**
- ✅ Chunk size ideale per paragrafi clinici (200-1000 chars)
- ✅ Overlap 20% cattura contesto tra chunk adiacenti
- ✅ Separatori rispettano struttura naturale del testo
- ✅ Performance retrieval eccellente (top similarity ~0.65)
- ✅ Bassa latenza (<500ms per search con 603 chunks)
- ✅ Citazioni leggibili (estratti di 1-2 paragrafi)

**Contro:**
- ⚠️ Non semanticamente consapevole (split meccanico)
- ⚠️ Possibili split subottimali in liste/tabelle complesse

**Metriche:**
- Total chunks: 603 (11 documenti)
- Avg chunk size: ~650 chars (range: 200-800)
- Retrieval precision@5: ~85% (query test "radicolopatia lombare")
- Retrieval latency: <500ms
- Storage overhead: Moderato (160 chars overlap)

### 2. FixedSizeChunker (500/100)

**Configurazione:**
```python
{
    "chunk_size": 500,
    "chunk_overlap": 100
}
```

**Pro:**
- ✅ Chunk più piccoli = maggiore granularità
- ✅ Latency retrieval inferiore

**Contro:**
- ❌ Chunk troppo piccoli perdono contesto clinico completo
- ❌ Maggior numero di chunk = più embedding costs
- ❌ Citazioni frammentate (difficili da leggere)
- ❌ Precision ridotta su query complesse

**Metriche Stimate:**
- Total chunks: ~900 (50% in più)
- Retrieval precision@5: ~70%
- Storage overhead: Alto

**Decisione:** ❌ Scartata per perdita di contesto e maggiori costi

### 3. RecursiveCharacterTextSplitter (1500/300)

**Configurazione:**
```python
{
    "chunk_size": 1500,
    "chunk_overlap": 300
}
```

**Pro:**
- ✅ Chunk più grandi = contesto più ricco
- ✅ Meno chunk totali = meno embedding costs

**Contro:**
- ❌ Chunk troppo grandi possono includere topics multipli
- ❌ Recall ridotta (informazione specifica diluita)
- ❌ Latenza LLM più alta (context più lungo)
- ❌ Citazioni troppo lunghe (UX degradata)

**Metriche Stimate:**
- Total chunks: ~400 (33% in meno)
- Retrieval precision@5: ~75%
- LLM latency: +20-30%

**Decisione:** ❌ Scartata per recall ridotta e UX citazioni

### 4. SemanticChunker (Similarity-based)

**Configurazione:**
```python
{
    "method": "percentile",
    "breakpoint_threshold_type": "percentile",
    "breakpoint_threshold_amount": 95
}
```

**Pro:**
- ✅ Chunking semanticamente consapevole
- ✅ Rispetta naturalmente i confini semantici
- ✅ Potenzialmente migliore coerenza interna chunk

**Contro:**
- ❌ Computazionalmente costoso (embedding per ogni sentence)
- ❌ Latenza ingestion significativamente maggiore (~5x)
- ❌ Variabilità dimensione chunk (range molto ampio)
- ❌ Difficile predire numero chunk risultante
- ❌ Overhead OpenAI API calls per sentence embeddings

**Metriche Stimate:**
- Total chunks: ~500-700 (variabile)
- Ingestion latency: +400-500%
- Retrieval precision@5: ~87% (marginal gain)
- Costs: Significativamente più alti

**Decisione:** ❌ Scartata per costi/latency vs marginal benefit

## Benchmark Retrieval - Query Test Set

### Metodologia

- **Query Set**: 10 query rappresentative delle domande utente tipiche
- **Metric**: Precision@5 (rilevanza dei top-5 chunk recuperati)
- **Valutazione**: Manuale (esperti dominio verificano pertinenza)
- **Tool**: RPC `match_document_chunks` con cosine similarity

### Risultati per Strategia Adottata (800/160)

| Query | Top Similarity | Chunks Rilevanti (su 5) | Note |
|-------|---------------|------------------------|------|
| "radicolopatia lombare sintomi" | 0.649 | 5/5 | Ottimo: tutti chunk pertinenti |
| "differenza lombare cervicale" | 0.612 | 4/5 | Buono: 1 chunk marginale |
| "trattamento lombalgia" | 0.588 | 5/5 | Ottimo |
| "esercizi posturali" | 0.571 | 3/5 | Discreto: query generica |
| "anatomia colonna vertebrale" | 0.623 | 4/5 | Buono |
| "diagnosi ernia discale" | 0.605 | 5/5 | Ottimo |
| "riabilitazione post-operatoria" | 0.556 | 4/5 | Buono |
| "prevenzione dolore cronico" | 0.542 | 3/5 | Discreto: topic ampio |
| "mobilizzazione articolare" | 0.597 | 5/5 | Ottimo |
| "valutazione funzionale" | 0.580 | 4/5 | Buono |

**Precision@5 Media:** 84% (42/50 chunk rilevanti)

### Confronto con Altre Strategie (Stima)

| Strategia | Precision@5 | Avg Latency | Total Chunks | Relative Cost |
|-----------|-------------|-------------|--------------|---------------|
| **800/160 (adottata)** | **84%** | **450ms** | **603** | **1.0x** |
| 500/100 | 72% | 380ms | ~900 | 1.5x |
| 1500/300 | 78% | 520ms | ~400 | 0.7x |
| SemanticChunker | 87% | 480ms | ~650 | 5.0x (ingestion) |

## Considerazioni Specifiche per Fisioterapia

### Natura dei Documenti

- **Struttura**: Paragrafi clinici, liste, procedure step-by-step
- **Lunghezza Media Paragrafo**: 300-800 caratteri
- **Informazioni Chiave**: Sintomi, diagnosi, trattamenti spesso in paragrafi dedicati
- **Terminologia**: Tecnica ma accessibile (no formule matematiche complesse)

### Chunk Size 800 Rationale

1. **Un paragrafo clinico completo**: 800 chars cattura 1-2 paragrafi medi
2. **Contesto sufficiente**: Sintomo + possibile causa/trattamento
3. **Leggibilità citazioni**: Estratti comprensibili senza contesto aggiuntivo
4. **Token LLM**: ~200 tokens/chunk, lascia ampio margine per context window

### Overlap 160 (20%) Rationale

1. **Cattura transizioni**: Informazioni a cavallo tra paragrafi
2. **Non eccessivo**: 20% è sweet spot (storage vs recall)
3. **Ridondanza benefica**: Stesso concetto in chunk adiacenti aumenta recall

## Metriche Post-Deployment

### Observability

Log metriche su ogni retrieval:
```json
{
  "query": "...",
  "top_similarity": 0.645,
  "chunks_returned": 5,
  "retrieval_time_ms": 428,
  "chunk_strategy": "recursive_character_800_160"
}
```

### Alert & Monitoring

- **Low Similarity Threshold**: Alert se top_similarity < 0.4 (indica query fuori dominio o KB gap)
- **High Retrieval Latency**: Alert se retrieval_time_ms > 1000ms
- **Chunk Coverage**: Monitorare % query con ≥3 chunk rilevanti (target: >80%)

### Iterazione Futura

Rivalutare strategia chunking quando:
- Knowledge base cresce >100 documenti
- Precision@5 scende sotto 75%
- Feedback utenti indica citazioni inadeguate
- Nuovi modelli embedding disponibili (es. OpenAI text-embedding-3)

## References

- **Implementation**: `apps/api/api/ingestion/chunking/recursive.py`
- **Configuration**: `apps/api/api/ingestion/chunking/strategy.py`
- **Verification Script**: `scripts/validation/verify_chunk_ids.py`
- **LangChain Docs**: https://python.langchain.com/docs/modules/data_connection/document_transformers/
- **Story 2.10**: Initial ingestion con fallback strategy
- **Story 2.11**: Definizione e applicazione strategia ottimale

## Appendix: Re-Ingestion Procedure

Se necessario cambiare strategia chunking:

1. **Backup chunks attuali**:
   ```sql
   CREATE TABLE document_chunks_backup AS SELECT * FROM document_chunks;
   ```

2. **Aggiorna strategia in config**:
   ```python
   CHUNKING_STRATEGY = "recursive_character"
   CHUNK_SIZE = 800
   CHUNK_OVERLAP = 160
   ```

3. **Cancella chunks esistenti** (preserva documenti):
   ```sql
   DELETE FROM document_chunks;
   ```

4. **Re-ingest documenti**:
   ```bash
   cd apps/api
   poetry run python -m api.ingestion.ingest_documents
   ```

5. **Verifica integrità**:
   ```bash
   python scripts/validation/verify_chunk_ids.py
   poetry run pytest tests/test_chunk_integrity.py
   ```

6. **Validazione retrieval**:
   ```bash
   # Test query set su nuovo chunking
   poetry run pytest tests/test_chat_nfr.py
   ```

## Conclusioni

La strategia **RecursiveCharacterTextSplitter (800/160)** rappresenta il miglior compromesso per:
- ✅ Qualità retrieval (precision@5: 84%)
- ✅ Performance (latency <500ms)
- ✅ Costi ragionevoli (603 chunks)
- ✅ UX citazioni (estratti leggibili)

Mantiene flessibilità per iterazioni future basate su dati reali di utilizzo.

