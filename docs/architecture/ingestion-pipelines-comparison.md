# Ingestion Pipelines Comparison

**Story:** 6.1 – Pipeline Documentation & Watcher Enhancement  
**Version:** 1.0 (2025-10-17)  
**Autore:** Team Architettura FisioRAG

## Executive Overview

Il sistema di ingestion dispone di **due pipeline distinte** che condividono storage e chunking router, ma differiscono per trigger, capacità LLM e livello di controllo operativo:

- **Pipeline A – Watcher (Automatica):** monitora la cartella `INGESTION_WATCH_DIR`, elabora solo file nuovi o modificati, ora integra estrazione avanzata, classificazione con feature flag e osservabilità AC7.
- **Pipeline B – API Sync Jobs (Manuale):** attivata da operatori tramite endpoint `/knowledge-base/sync`, offre controllo esplicito dei metadati, batch embedding e progress tracking.

Comprendere differenze, trade-off e casi d’uso permette rollout mirati, prevenendo gap di qualità tra ingestion automatica e manuale.

## Feature Matrix

| Capability | Pipeline A – Watcher | Pipeline B – API Sync Jobs | Note |
| :--- | :--- | :--- | :--- |
| **Trigger** | File system watcher (`scan_once` async) | REST endpoint (admin authenticated) | Watcher async DB-first (Story 6.3); API gestisce batch asincroni |
| **Estrattore** | `DocumentExtractor` (PyMuPDF, python-docx, fallback txt) | `DocumentExtractor` identico | Uniformità post Story 6.1 |
| **Metadata** | `images_count`, `tables_count`, hash, routing info | Metadata custom inviati dal client + extraction | Watcher scrive metadata base, API accetta payload arricchiti |
| **Classificazione** | `classify_content_enhanced` con flag `WATCHER_ENABLE_CLASSIFICATION` (default `true`) e timeout 10s | `classify_content_enhanced` sempre attiva | Watcher effettua graceful fallback (timeout/error) |
| **Caching** | Redis cache condivisa (`classification_cache`) opzionale | Idem | Governance costi: watcher classifica solo file nuovi/modificati |
| **Chunking** | `ChunkRouter` → `recursive_character_800_160` o `tabular_structural` con fallback controllato | Stesse strategie, più parametri configurabili | Nomi strategia uniformati per AC4 |
| **Persistenza** | **DB-first storage + Concurrency Safety** (Story 6.3+6.4): `save_document_to_db`, `save_chunks_to_db` via asyncpg. Advisory locks PostgreSQL coordinano embedding generation batch/watcher (AC2.5) | DB + Vector store via `index_chunks` | Watcher: blocking `pg_advisory_lock`; Batch: non-blocking `pg_try_advisory_lock` (skip locked) |
| **Embedding Generation** | **Sync post-ingestion** (Story 6.4 AC2): chiamata `index_chunks()` dopo `save_chunks_to_db()` con advisory lock blocking. Genera embeddings OpenAI + salva su Supabase vector store. Fallback graceful: errori non bloccano ingestion | **Sync inline** (già esistente): embeddings generati durante sync job via `index_chunks()` o Celery task asincrono (`kb_indexing_task`) | Watcher: coordinamento via PostgreSQL advisory locks con batch script; gestisce retry automatico OpenAI (tenacity) |
| **Osservabilità** | Nuove metriche: latenza p50/p95/p99, success/failure ratio, fallback ratio, strategy distribution, cache hit-rate | Logging esistente (timing per extraction/classification/chunking) | Watcher esporta snapshot via `get_watcher_metrics_snapshot` |
| **Uso tipico** | Drop folder automatizzato, import massivo non supervisionato | Upload curato, scenari che richiedono metadati custom o reprocess target | |
| **Fallback** | Timeout → default strategy; confidenza <0.7 → fallback dichiarato | Manuale decide se ripetere job con parametri custom | |
| **SLO** | p50 < 1.5s, p95 < 5s, fallback < 15%, cache hit ≥ 40% | Dipende dal carico manuale; orientato a qualità | |

## Pipeline Profiles

### Pipeline A – Watcher (Automatica)

- **Trigger:** `async def scan_once(IngestionConfig, inventory, settings, conn)` invocato da worker async `watcher_runner.py` (Story 6.3).
- **Pipeline Mode:** **Async** con asyncpg pool per DB operations. Event loop non-bloccante per I/O efficiente.
- **Feature Flag:** `WATCHER_ENABLE_CLASSIFICATION=true` (default). Disabilitandolo si ottiene comportamento legacy pre-6.1.
- **Timeout:** `CLASSIFICATION_TIMEOUT_SECONDS=10` (range 1–60). In caso di scadenza → fallback con log `watcher_classification_timeout`.
- **Extraction:** `DocumentExtractor` con PyMuPDF (PDF), python-docx (DOCX), fallback UTF-8/latin-1 (TXT). Propaga `images_count`, `tables_count` nei metadata del documento.
- **Classification:** invocata solo per file nuovi/modificati (hash inventario). Esegue in thread pool, registra sorgente (`cache`, `llm`, `unknown`), latenza, confidence.
- **Routing:** `ChunkRouter` con soglia confidenza 0.7. Strategia registrata in `Document.chunking_strategy`. In fallback log di motivazione (`classification_absent`, `low_confidence`, `classification_timeout`, `unmapped_category`).
- **Observability:** struttura JSON logging (`watcher_classification_start/success/error`, `watcher_chunking_fallback`, `watcher_db_storage_complete`, `watcher_async_scan_complete`, `watcher_metrics_snapshot`). Metriche aggregate accessibili via `get_watcher_metrics_snapshot`.
- **Persistenza:** **DB-first storage (Story 6.3)** - salva documento, chunks e metadata nel database PostgreSQL via asyncpg con transazione atomica. **Concurrency safety (Story 6.4 AC2.5)**: usa `pg_advisory_lock(hashtext('docs_ns'), hashtext(document_id))` per coordinare embedding generation con batch script. Lock DB-side con `hashtext()` garantisce stabilità cross-process. File JSON legacy rimossi.
- **Embedding Generation (Story 6.4 AC2):** dopo `save_chunks_to_db()`, chiama `index_chunks()` per generare embeddings OpenAI e salvare su Supabase vector store. Usa advisory lock blocking per coordinamento con batch script. Fallback graceful: errori indexing non bloccano ingestion principale (log warning + batch script come fallback).

### Pipeline B – API Sync Jobs (Manuale)

- **Trigger:** endpoint FastAPI `POST /knowledge-base/sync`. Richiede token admin e payload con path sorgente o testo inline.
- **Control Plane:** restituisce job id, tracking stato (`sync_jobs_store`). Supporta batch embedding asincrono via Celery.
- **Extraction & Classification:** stessi componenti del watcher, ma eseguiti nel contesto request/response. Permette override di metadata e parametri chunking.
- **Chunk Persistance:** salva su DB (documento + chunk metadata) e indicizza su Supabase (pgvector). Gestisce update status (processing → completed/failed).
- **Logging:** `pipeline_complete`, `chunking_complete`, timing breakdown per extraction/classification/chunking/indexing.
- **Use Cases:** onboarding documenti curati, migrazioni, reprocess manuale con parametri custom, QA-driven ingestion.

## Trade-Off Analysis

- **Automazione vs Controllo:** Watcher è zero-touch ma seriale; pipeline manuale richiede intervento umano ma offre visibilità completa su job state.
- **Qualità contenuto:** Con Story 6.1 entrambi sfruttano classificazione avanzata e chunking intelligente; differenze principali riguardano arricchimento metadata aggiuntivi forniti manualmente.
- **Costi & Performance:** Watcher utilizza feature flag e cache per governare costi LLM; pipeline manuale può forzare re-classification su richieste specifiche.
- **Operatività:** Watcher idoneo a drop folder automatiche; API sync preferibile per import mission critical con validazioni/rollback mirati.

## Flow Diagrams

### Pipeline A – Watcher

```mermaid
flowchart TD
    W0[File System Watcher] --> W1[Compute SHA-256]
    W1 -->|Hash invariato| WEnd[Skip]
    W1 -->|Nuovo hash| W2[DocumentExtractor]
    W2 --> W3{Classification Enabled?}
    W3 -->|No| W5[ChunkRouter Fallback]
    W3 -->|Yes| W4[Enhanced Classification (timeout 10s)]
    W4 -->|Success| W5
    W4 -->|Timeout/Error| W5
    W5 --> W6[Save Content + Chunks + Metadata]
    W6 --> W7[Embedding Generation + Advisory Lock]
    W7 -->|Success| W8[Update Inventory + Metrics Snapshot]
    W7 -->|Error| W8
    W8 --> WEnd[Complete]
```

### Pipeline B – API Sync Jobs

```mermaid
flowchart TD
    A0[Admin Request /sync] --> A1[Load Payload]
    A1 --> A2[DocumentExtractor]
    A2 --> A3[Enhanced Classification]
    A3 --> A4[ChunkRouter]
    A4 --> A5[Persist Document + Chunk Metadata]
    A5 --> A6[Embed + Index (Celery or Sync)]
    A6 --> A7[Update Job Status + Logs]
```

## Observability Checklist

- **Watcher Metrics:** attraverso `get_watcher_metrics_snapshot()` o log `watcher_metrics_snapshot` (include latenza p50/p95/p99, success/failure ratio, fallback ratio, strategy distribution, cache stats).
- **Alerting:** configurare warning per `fallback_ratio > 0.20`, failure rate >10%, p95 latency >5s (AC7).
- **Dashboard Suggestion:** esportare snapshot verso Grafana/Prometheus tramite task periodico che richiama la funzione esposta.

## Correlazioni & Riferimenti

- `apps/api/api/ingestion/watcher.py` – implementazione aggiornata con DocumentExtractor, classificazione, metriche.
- `apps/api/api/routers/knowledge_base.py` – pipeline manuale e indexing.
- `docs/architecture/addendum-chunking-strategy-benchmark.md` – benchmark strategie chunking, ora condivise da entrambe le pipeline.
- `docs/architecture/addendum-langchain-rag-debug-patterns.md` – linee guida per debugging e ispezione chunking.
