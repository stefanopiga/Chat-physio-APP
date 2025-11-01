# Classification Cache Design (Story 2.9)

**Data:** 2025-10-14  
**Autore:** James (Dev Agent)  
**Riferimento:** Story 2.9 – Classification Performance Optimization

---

## Contesto

I test P95 dell'ingestione documentale (Story 2.7) hanno evidenziato un collo di bottiglia critico: ogni documento viene classificato tramite GPT-5 Nano con chiamata sincrona, producendo una latenza media di **11.4s** e rendendo impossibile la gestione di carichi concorrenti. Obiettivo della Story 2.9: ridurre la latenza percepita dagli endpoint di ingestion tramite caching aggressivo dei risultati di classificazione.

Redis è già presente nell'infrastruttura (Celery broker) e quindi rappresenta la scelta naturale per introdurre un layer di cache a bassa latenza.

---

## Decisioni di Design

### 1. Storage Engine
- **Redis** viene riutilizzato come datastore in-memory, con database isolato (`DB 1`) per separare i dati della cache dal traffico Celery.
- Connessione configurabile tramite `CLASSIFICATION_CACHE_REDIS_URL`; default derivato dal broker Celery (`+1` rispetto al DB corrente) con fallback `redis://localhost:6379/1`.

### 2. Chiave di Cache Deterministica
- Chiave calcolata come `classification:v1:{sha256(text + metadata)}`.
- Il metadata viene serializzato in JSON deterministico (keys ordinati, conversione value non serializzabili) per garantire coerenza tra worker/ambienti.
- Versionamento (`v1`) consente future evoluzioni del formato senza invalidare manualmente tutte le entry.

### 3. TTL & Policy
- TTL predefinito **7 giorni** (`CLASSIFICATION_CACHE_TTL_SECONDS`, default 604800). Valore scelto per coprire cicli di aggiornamento contenuti ma limitare il rischio di staleness.
- Flag runtime `CLASSIFICATION_CACHE_ENABLED` permette rollback immediato senza deploy.
- Funzione `delete_by_digest` introdotta per invalidare manualmente entry specifiche tramite endpoint admin.

### 4. Fallback Garantito
- In caso di errore Redis (connessione, serializzazione, timeouts) la cache degrada in modo trasparente: viene registrato `classification_cache_error` e la pipeline invoca comunque l'LLM, preservando la compatibilità.
- Se il flag è disabilitato o Redis non disponibile all'avvio, l'istanza viene creata in modalità `enabled=False` evitando ulteriori tentativi.

### 5. Observability & Metrics
- Eventi strutturati: `classification_cache_hit`, `classification_cache_miss`, `classification_cache_error`, `classification_cache_delete`, `classification_cache_ready`.
- Metriche aggregate in memoria (rolling window 1000 campioni): hit/miss counters, hit-rate, latenza p50/p95 per hit e miss.
- Endpoint admin aggiuntivo:
  - `GET /api/v1/admin/knowledge-base/classification-cache/metrics` → payload dashboard-ready (`enabled`, `hits`, `misses`, `hit_rate`, `latency_ms`, `ttl_seconds`, `redis_url`).
  - `DELETE /api/v1/admin/knowledge-base/classification-cache/{digest}` → invalidazione manuale.

---

## Implementazione Principale

| Componente | Descrizione |
|------------|-------------|
| `apps/api/api/knowledge_base/classification_cache.py` | Nuovo modulo singleton `ClassificationCache` con gestione Redis, hashing, TTL e metrics. |
| `apps/api/api/knowledge_base/classifier.py` | Integrazione cache in `classify_content_enhanced`: lookup prima dell'LLM, salvataggio post-invocazione, tracking latenza. |
| `apps/api/api/config.py` | Nuove settings Pydantic (`classification_cache_*`). |
| `apps/api/api/routers/admin.py` | Endpoint admin per metriche e invalidazione. |
| ENV templates (`.env`, `.env.test.local`, `ENV_TEST_TEMPLATE`, `ENV_STAGING_TEMPLATE`, `scripts/perf/.env.staging.local`) | Variabili ambiente aggiuntive. |

---

## Considerazioni Future

1. **Cache Invalidation Smart** – In Story future valutare un event hook sul ciclo di vita dei documenti (es. update metadata) per invalidare automaticamente la cache anziché affidarsi solo a TTL/manuale.
2. **Distributed Metrics** – In prospettiva multi-instance, spostare le metriche su Prometheus / Pushgateway anziché in memoria locale.
3. **Compressione Payload** – Se i risultati Pydantic crescono di dimensione considerare compressione (es. zstd) per ridurre footprint Redis.
4. **Shard/Replica Redis** – Monitorare memoria e latenza; se i volumi crescono valutare un cluster Redis dedicato o politiche `maxmemory` + eviction LRU.

---

## Stato Validazione

| Test | Stato | Note |
|------|-------|------|
| Unit: cache hit/miss/TTL/error | ✅ | `apps/api/tests/test_classification_cache.py` |
| Integration: pipeline con cache | ✅ | `apps/api/tests/test_classification_cache_pipeline.py` |
| Performance: `run_p95.ps1` | ✅ | Vedi `reports/metrics-p95-20251014-post-cache.md` |

---

## Allegati

- `reports/metrics-p95-20251014-post-cache.md` – risultati test P95 post-implementazione.
- Log FastAPI: verificare eventi `classification_cache_*` in `api` logger per audit.

