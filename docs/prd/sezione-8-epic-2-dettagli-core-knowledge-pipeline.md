# Sezione 8: Epic 2 Dettagli - Core Knowledge Pipeline

**Goal dell'Epic**: Implementare il backend per l'ingestione intelligente dei documenti, inclusa l'analisi, il chunking dinamico e l'indicizzazione nella base di conoscenza vettoriale, rendendo il sistema pronto a rispondere alle domande.

#### **Story 2.1: Document Loader & Text Extractor**
*   **As a** Sviluppatore Backend, **I want** un servizio per monitorare una directory ed estrarre testo da `.docx` e `.pdf`, **so that** il contenuto sia preparato per l'analisi.
**Acceptance Criteria:** 1. Il servizio accede a una directory di file. 2. Scansiona file nuovi/modificati. 3. Il testo viene estratto correttamente. 4. Il contenuto viene salvato temporaneamente. 5. Gestisce errori di parsing.

#### **Story 2.2: Structural Analysis Meta-Agent**
*   **As a** Sviluppatore Backend, **I want** integrare un meta-agente LLM per classificare la struttura di un documento, **so that** possiamo decidere la strategia di chunking.
**Acceptance Criteria:** 1. Prompt per classificare e motivare. 2. Il backend riceve classificazione e motivazione. 3. Classificazione, motivazione e confidenza sono loggati. 4. Almeno 3 categorie di classificazione definite.

#### **Story 2.3: Polymorphic Chunking Router**
*   **As a** Sviluppatore Backend, **I want** implementare diverse strategie di chunking e un router, **so that** il testo venga suddiviso in blocchi ottimizzati.
**Acceptance Criteria:** 1. Almeno due strategie di chunking implementate. 2. Definita una strategia di fallback. 3. Il sistema applica la strategia corretta o il fallback. 4. Il testo viene suddiviso in chunk con riferimento alla sorgente. 5. Design modulare.

#### **Story 2.4: Vector Indexing in Supabase**
*   **As a** Sviluppatore Backend, **I want** calcolare embedding per ogni chunk e salvarli in Supabase, **so that** la base di conoscenza sia ricercabile semanticamente.
**Acceptance Criteria:** 1. Configurazione API per servizio di embedding. 2. Calcolo embedding per ogni chunk. 3. Salvataggio di chunk, embedding e metadati su Supabase. 4. Tabella configurata con indice per ricerca di similarità. 5. Processo attivabile da endpoint admin.

**Reliability (Job Asincroni)**
- Il processo di indicizzazione deve essere eseguito come job asincrono tramite Celery con Redis come broker e result backend.
- L'avvio del job restituisce un `jobId` (alias `task_id` Celery) tramite endpoint admin.
- È disponibile un endpoint per consultare lo stato del job: `GET /admin/knowledge-base/sync-jobs/{jobId}` con stati `PENDING/STARTED/SUCCESS/FAILURE/RETRY` e risultato/errore quando disponibile.
- Devono essere attivi retry automatici con backoff esponenziale e jitter per errori transienti (max 5 tentativi).
- I risultati devono avere scadenza configurata (`result_expires`, default 1 giorno) con politica di cleanup in ambienti persistenti.
- Security: usare serializer `json` per task/result, evitare `pickle`.
- Caveat Redis: evitare ETA/countdown lunghi; se necessario, configurare `visibility_timeout` coerente.

---

## Requisiti di Performance

- Ricerca Semantica (API backend): Il 95° percentile (p95) della latenza delle richieste di ricerca semantica deve essere < 500ms.
- Misurazione: La latenza sarà misurata lato backend includendo tempo di query vettoriale su Supabase/pgvector e serializzazione della risposta.
- Enforcement: Il requisito sarà tracciato in ambienti di staging e produzione; deviazioni significative richiederanno azioni correttive prima del rilascio.

## API Amministrative per Job Asincroni

- `POST /admin/knowledge-base/sync-jobs` → crea un job Celery di indicizzazione e restituisce `{ jobId }`.
- `GET /admin/knowledge-base/sync-jobs/{jobId}` → restituisce `{ jobId, state, result? | error? }` leggendo dal result backend.

## Operatività

- Dipendenze: `pip install -U "celery[redis]"`.
- Avvio worker: `celery -A apps.api.api.celery_app.celery_app worker --loglevel=INFO`.
- (Opzionale) `celery beat` per cleanup `result_expires`.
- Riferimenti: Documentazione Celery su Redis (installazione, configuration/visibility timeout, results), Tasks (Retry/Automatic retry, States), First steps (AsyncResult.get()).
- Ambiente VPS di riferimento: Ubuntu 22.04.5 LTS. [Fonte: terminale utente (Welcome to Ubuntu 22.04.5 LTS)]

