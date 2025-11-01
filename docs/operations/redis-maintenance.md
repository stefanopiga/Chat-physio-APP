# Redis Maintenance – Classification Cache

**Ultimo aggiornamento:** 2025-10-14

Story 2.9 introduce un database Redis dedicato (default DB=1) per la cache della classificazione documenti.

## Configurazione

- Variabili ambiente principali:
  - `CLASSIFICATION_CACHE_ENABLED` (default: `true`)
  - `CLASSIFICATION_CACHE_TTL_SECONDS` (default: `604800`)
  - `CLASSIFICATION_CACHE_REDIS_URL` (facoltativa – sovrascrive URL di default derivato dal broker Celery)
- Namespace chiavi: `classification:v1:{sha256}`.

## Operazioni di manutenzione

1. **Verificare stato cache**
   - Endpoint admin: `GET /api/v1/admin/knowledge-base/classification-cache/metrics`
   - Output include hit-rate, p50/p95 latency, TTL, URL Redis utilizzato.

2. **Invalidare entry specifica**
   - `DELETE /api/v1/admin/knowledge-base/classification-cache/{digest}`
   - `digest` è l'hash SHA-256 calcolato su testo + metadata.

3. **Flush completo del namespace**
   - `DELETE /api/v1/admin/knowledge-base/classification-cache`
   - Utilizzare solo previo coordinamento con il team ingestion.

4. **Disabilitare rapidamente la cache**
   - Set `CLASSIFICATION_CACHE_ENABLED=false` e riavviare l'API.
   - Nessun side-effect: la pipeline torna a invocare direttamente l'LLM.

## Monitoraggio

- Log strutturati (`classification_cache_hit`, `classification_cache_miss`, `classification_cache_error`, `classification_cache_flush`).
- Verificare saturazione memoria Redis tramite `INFO memory` o dashboard esistente.

## Troubleshooting rapido

| Sintomo | Possibile causa | Azione |
|--------|-----------------|--------|
| Nessun `classification_cache_ready` all'avvio | Redis URL errato o DB non raggiungibile | Verificare credenziali, eseguire `redis-cli PING` |
| Hit-rate ~0% post deploy | Cache non warmata | Eseguire ingest run per popolare il namespace prima dei test di carico |
| Errori `classification_cache_error` frequenti | Timeout o down Redis | Considerare fallback temporaneo (`CLASSIFICATION_CACHE_ENABLED=false`) e investigare cluster |

