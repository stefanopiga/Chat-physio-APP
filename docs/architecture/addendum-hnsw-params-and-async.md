# Addendum: Parametri HNSW e Stack Asincrono per Story 2.4

**Oggetto:** Proposta di completamento delle specifiche tecniche per la Story 2.4: Vector Indexing in Supabase

## Contesto

L'analisi della documentazione per la Story 2.4 ha evidenziato specifiche mancanti relative ai parametri di costruzione dell'indice HNSW e alla tecnologia per la gestione dei task asincroni. Questo addendum consolida le informazioni note e propone valori/tecnologie iniziali coerenti con le best practice indicate nella richiesta.
## 1. Specifiche Modello di Embedding

- **Modello**: `text-embedding-3-small` (OpenAI)
- **Dimensionalità**: `1536`

Motivazione: come da documentazione di progetto esistente.
## 2. Configurazione Indice Vettoriale (Supabase/pgvector)

- **Tabella**: `document_chunks`
- **Colonna Vettoriale**: `embedding VECTOR(1536)`
- **Tipo Indice**: `HNSW` con metrica `vector_cosine_ops`
- **Parametri Proposti**:
  - `m = 16`
  - `ef_construction = 64`
- **Statement SQL**:
```sql
CREATE INDEX ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

Motivazione: HNSW confermato dalla documentazione; valori iniziali standard bilanciano prestazioni e accuratezza e possono essere ottimizzati in seguito.
## 3. Gestione Task Asincroni (Backend FastAPI)

- **Stack proposto**: Celery con Redis come message broker
- **Endpoint previsto**: `GET /admin/knowledge-base/sync-jobs/{jobId}`
- **Motivazione**: Necessità di tracciare lo stato dei job di indicizzazione. Celery fornisce gestione dello stato, retry e osservabilità dei task, a differenza di `BackgroundTasks` di FastAPI.

Note operative:
- Definire task di indicizzazione documenti (enqueue su inserimento batch nella KB)
- Persistenza stato job via Celery backend (es. Redis o database dedicato)
- Mappare `jobId` con `task_id` Celery nell'endpoint di stato

## 4. Architettura per la Gestione dei Job Asincroni

### 4.1 Tecnologia Scelta
- **Task queue**: Celery
- **Broker/Backend**: Redis
- **Motivazione**: supporto a retry, stato dei job, visibilità operativa e scalabilità orizzontale.

### 4.2 Flusso End-to-End
1. Admin invoca `POST /admin/knowledge-base/sync-jobs` → creazione job di indicizzazione.
2. L'API enqueua il task Celery `kb.index_documents(batch_id|source)` e restituisce `jobId` (alias `task_id`).
3. Worker Celery esegue:
   - Caricamento chunk da sorgente
   - Calcolo embedding (OpenAI `text-embedding-3-small`) e validazione dimensione 1536
   - Inserimento su Supabase (`document_chunks`, funzione `match_document_chunks` disponibile per query)
4. Stato consultabile via `GET /admin/knowledge-base/sync-jobs/{jobId}` → legge lo stato dal backend Celery.

### 4.3 Retry e Gestione Errori
- **Retry**: abilitato per eccezioni transienti (es. timeout rete OpenAI/Supabase) con backoff esponenziale (es. `max_retries=5`, `countdown=2^n`).
- **Errori**:
  - Classificare `TRANSIENT` vs `FATAL` (es. schema DB mancante → FATAL, rate limit temporaneo → TRANSIENT).
  - Log strutturati con dettaglio causa e contesto (batch, document id).
- **Stati Job**: `PENDING` → `RUNNING` → `SUCCESS` | `FAILED`.

### 4.4 Idempotenza
- Calcolo embedding e insert devono essere idempotenti:
  - Verifica pre-inserimento con chiave naturale (`document_id` + `chunk_hash`) per evitare duplicati.
  - Upsert con conflitto su chiave unica (`on conflict do update`) per aggiornamenti sicuri.
  - Tracciare `updated_at` per distinguere re-run vs inserimento nuovo.

### 4.5 Osservabilità
- Metriche minime: conteggio job per stato, durata media job, error rate task.
- Logging: eventi di enqueue/dequeue, transizioni di stato, retry con numero tentativi.
- Collegamento con sezione `Monitoraggio e Osservabilità` (`docs/architecture/sezione-14-monitoraggio-e-osservabilit.md`).

## 5. Configurazione Operativa Celery + Redis

### 5.1 Dipendenze e Installazione
- Installare: `pip install -U "celery[redis]"`.
  - Fonte: "Using Redis — Celery 5.5.3 documentation", sezione Installation (`https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html`).

### 5.2 Configurazione di Base
```python
# apps/api/api/celery_app.py
from celery import Celery

celery_app = Celery(
    "api",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def my_indexing_task(self, payload: dict) -> dict:
    return {"status": "ok", "count": len(payload.get("items", []))}
```
- Broker URL: `redis://:password@hostname:port/db_number`, default `redis://localhost:6379/0`.
- Opzioni aggiuntive: Unix socket `redis+socket:///path/to/redis.sock`, Sentinel via `broker_transport_options`.
- Fonte: "Using Redis — Configuration" (`https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html`).

### 5.3 Avvio Servizi
- Worker: `celery -A apps.api.api.celery_app.celery_app worker --loglevel=INFO`.
  - Fonte: "First steps with Celery" (`https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html`).
- (Opzionale) Beat per cleanup risultati: attiva il task `celery.backend_cleanup` se `result_expires`>0.
  - Fonte: "Configuration — result_expires" (`https://docs.celeryq.dev/en/stable/userguide/configuration.html`).

### 5.4 Result Backend e Stato Job
- Redis come result backend (chiave `backend` o `app.conf.result_backend`).
- Stati standard: `PENDING`, `STARTED` (se tracking abilitato), `SUCCESS`, `FAILURE`, `RETRY`.
- Consultazione: `AsyncResult(task_id).state`, `get(propagate=False)`.
- Scadenza risultati: `result_expires` default 1 giorno.
- Fonti: "Using Redis — Results", "Tasks — States", "First steps — AsyncResult.get()" (stessa documentazione Celery ai link sopra citati).

### 5.5 Retry e Robustezza
- Retry manuale: `Task.retry()` con stato `RETRY` e mantenimento `task_id`.
- Retry automatico: `autoretry_for`, con `retry_backoff` esponenziale e `retry_jitter`.
- Esempio: `@app.task(autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, retry_kwargs={"max_retries": 5})`.
- Fonte: "Tasks — Retrying / Automatic retry" (`https://docs.celeryq.dev/en/stable/userguide/tasks.html`).

### 5.6 Visibility Timeout e Scheduling
- `broker_transport_options = {"visibility_timeout": 3600}` configurabile.
- Caveat Redis: evitare ETA/countdown lunghi; in alternativa usare scheduler DB-based o allineare i timeout.
- Fonte: "Using Redis — Visibility Timeout/Caveats" e "Calling — Warning" (`https://docs.celeryq.dev/en/stable/userguide/calling.html`).

### 5.7 Sicurezza
- Serializer: usare `json` per `task_serializer` e `result_serializer` (default dal 4.0).
- Motivazione: evitare l'uso di `pickle`.
- Fonte: "FAQ — Security" (`https://docs.celeryq.dev/en/stable/faq.html`).
