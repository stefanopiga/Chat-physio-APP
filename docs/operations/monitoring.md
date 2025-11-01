# Monitoring Playbook – Watcher Ingestion

Story 6.1 introduced full observability for the ingestion watcher.  
This runbook explains how to pull the metrics, export them in Prometheus format, and configure alert thresholds that match the project SLOs.

## Exposed Endpoints

| Endpoint | Description | Example |
| --- | --- | --- |
| `GET /metrics/watcher` | JSON snapshot (default) | `curl http://localhost:8000/metrics/watcher` |
| `GET /metrics/watcher?format=prometheus` | Prometheus text exposition | `curl http://localhost:8000/metrics/watcher?format=prometheus` |

The handler lives in `apps/api/api/routers/monitoring.py` and delegates to:

```python
snapshot = get_watcher_metrics_snapshot(settings)
format_metrics_for_prometheus(snapshot)
```

## Metric Fields

### JSON Payload Structure

```json
{
  "documents_processed": 12,
  "classification": {
    "success": 10,
    "failure": 2,
    "skipped": 0,
    "success_ratio": 0.8333,
    "failure_ratio": 0.1667
  },
  "classification_latency_ms": {
    "count": 12,
    "p50": 420.0,
    "p95": 910.0,
    "p99": 1025.0
  },
  "fallback": {
    "count": 1,
    "ratio": 0.0833
  },
  "strategy_distribution": {
    "counts": {
      "recursive_character_800_160": 7,
      "tabular_structural": 4,
      "fallback::recursive_character_800_160": 1
    },
    "ratio": {
      "recursive_character_800_160": 0.5833,
      "tabular_structural": 0.3333,
      "fallback::recursive_character_800_160": 0.0833
    }
  },
  "classification_cache": {
    "hits": 6,
    "misses": 4,
    "hit_rate": 0.6
  }
}
```

### Prometheus Export

`format_metrics_for_prometheus` publishes gauges and counters for:

- `watcher_documents_processed_total`
- `watcher_classification_success_total`, `watcher_classification_failure_total`, `watcher_classification_skipped_total`
- `watcher_success_ratio`, `watcher_failure_ratio`
- `watcher_fallback_total`, `watcher_fallback_ratio`
- `watcher_classification_latency_ms_{p50,p95,p99}`
- `watcher_strategy_count{strategy="..."}` and `watcher_strategy_ratio{strategy="..."}`
- `watcher_classification_cache_hit_rate`

> **Tip:** Schedule a small collector (cron/sidecar) to push the Prometheus output to Grafana/Prometheus Pushgateway when running outside Kubernetes.

## Alert Thresholds

| Metric | Threshold | Severity | Rationale |
| --- | --- | --- | --- |
| Fallback ratio | `> 0.20` | warning | signals routing regressions or classifier timeouts |
| Classification failure ratio | `> 0.10` | warning | API errors / timeouts impacting quality |
| Classification latency p95 | `> 5s` | critical | violates staging/production SLO |
| Cache hit-rate | `< 0.40` | warning | indicates Redis cache drift or cold cache |

Configure these alerts in Grafana/Prometheus or your monitoring stack of choice. Reference defaults live in `apps/api/api/config.py` (`WATCHER_ENABLE_CLASSIFICATION`, `CLASSIFICATION_TIMEOUT_SECONDS`) and can be overridden per environment.

## Validation Checklist

1. Hit `/metrics/watcher` after processing sample files – verify metadata counts, strategy distribution, and cache snapshot update.
2. Run automated tests to ensure coverage stays above 85%:  
   `poetry run pytest tests/test_watcher_enhanced.py tests/test_watcher_metrics.py -v --cov=api.ingestion.watcher --cov=api.ingestion.watcher_metrics`
3. Before production deploy, capture staging metrics and confirm SLO targets: p50 < 1.5s, p95 < 5s, fallback ratio < 15%, cache hit-rate ≥ 40%.

## Troubleshooting

- **Missing metrics:** call `reset_watcher_metrics()` in a Python REPL or restart the worker to clear stale state.
- **Cache stats empty:** ensure Redis is reachable; see `docs/reports/classification-cache-design.md`.
- **High fallback ratio:** inspect watcher logs (`watcher_chunking_fallback`) to determine whether low confidence or classification errors are driving fallbacks.

## Troubleshooting Watcher

### Quick Diagnostics
- Run `scripts/ops/watcher-debug.sh` (or `.ps1` on Windows) to capture docker status, logs, disk usage, git metadata, and the current redacted settings snapshot under `ingestion/temp/watcher-debug/<timestamp>/`.
- Execute `poetry --directory apps/api run python -m api.debug.print_settings` to inspect effective configuration values with secrets redacted and warnings for environment overrides.
- Validate the ingestion pipeline on a single file with `poetry --directory apps/api run python -m api.ingestion.run_diag --file <path>`; the command prints timings, routing decisions, and saves a JSON report in `ingestion/temp/diag/<timestamp>.json`.
- **Story 6.3:** Run watcher async with `poetry --directory apps/api run python scripts/watcher_runner.py` to execute a single watcher scan with DB-first storage (asyncpg pool integration).

### 429 vs Timeout Guidance
- **HTTP 429 spikes:** confirm that the watcher classification timeout is not below the recommended value (20s in development, 10s in production) and that retry policies are not exhausting the LLM quota.
- **Timeouts:** inspect the diagnostic report for `classification.status = "timeout"` and verify Redis connectivity logs (`redis_health_*`). Increase the timeout only after confirming that Redis and the LLM endpoint are healthy.

### Configuration Precedence
- `Settings` overrides take precedence over process environment variables, which in turn override `.env` defaults.
- `print_settings` logs a warning (when `DEBUG=true`) any time a process environment variable supersedes critical keys such as `OPENAI_API_KEY`, `INGESTION_WATCH_DIR`, or `CLASSIFICATION_TIMEOUT_SECONDS`.
- Use the output to confirm that ingestion paths resolve from the expected source (`settings`, `env`, or `default`) and that directories are created under the application temp tree.

### Post-deploy Checklist
- [ ] Run the watcher debug script to archive docker state and metrics.
- [ ] Execute the single-file diagnostic runner on a representative document and review the generated report.
- [ ] Confirm that Redis health checks report `redis_health_ok` (or `redis_health_skipped` when the cache is disabled).
- [ ] Re-run automated watcher tests (`pytest apps/api/tests/test_watcher_config.py apps/api/tests/test_redis_graceful.py apps/api/tests/test_watcher_diag.py`) to ensure coverage stays above the 85% target.

---

## Embedding Health Monitoring

**Story 6.4** introduced comprehensive embedding health monitoring to track vector indexing coverage and prevent RAG query failures.

### Health Endpoint

**Endpoint:** `GET /api/v1/admin/debug/embedding-health`  
**Auth:** Admin JWT required  
**Rate Limit:** 10 requests/hour

**Response Structure:**
```json
{
  "summary": {
    "total_documents": 2,
    "total_chunks": 190,
    "chunks_with_embeddings": 190,
    "chunks_without_embeddings": 0,
    "embedding_coverage_percent": 100.0,
    "last_indexed_at": "2025-10-20T17:17:26.763415+00:00"
  },
  "by_document": [
    {
      "document_id": "uuid",
      "document_name": "document.pdf",
      "total_chunks": 100,
      "chunks_with_embeddings": 100,
      "coverage_percent": 100.0,
      "last_indexed_at": "2025-10-20T15:30:00Z",
      "status": "COMPLETE"  // COMPLETE | PARTIAL | NONE
    }
  ],
  "warnings": []  // Populated if coverage <100% for any document
}
```

### Diagnostic Queries

**Check embedding coverage:**
```sql
SELECT COUNT(*) AS total_chunks,
       COUNT(embedding) AS with_embeddings,
       COUNT(*) - COUNT(embedding) AS without_embeddings,
       ROUND((COUNT(embedding)::numeric / COUNT(*)) * 100, 2) AS coverage_percent
FROM document_chunks;
```

**Per-document breakdown:**
```sql
SELECT d.id, d.file_name,
       COUNT(dc.id) AS total_chunks,
       COUNT(dc.embedding) AS with_embeddings,
       ROUND((COUNT(dc.embedding)::numeric / NULLIF(COUNT(dc.id), 0)) * 100, 2) AS coverage_percent,
       MAX(dc.updated_at) AS last_indexed_at
FROM documents d
LEFT JOIN document_chunks dc ON d.id = dc.document_id
WHERE d.status = 'completed'
GROUP BY d.id, d.file_name
ORDER BY coverage_percent ASC;
```

### Symptoms of RAG Blocking

**Zero results from semantic search:**
- Chat endpoint returns "Nessun contenuto rilevante trovato"
- `perform_semantic_search()` returns empty array
- Cause: chunks have `embedding=NULL`

**Fix procedure:**
1. **Verify coverage:**
   ```bash
   curl -H "Authorization: Bearer $ADMIN_TOKEN" \
        http://localhost/api/v1/admin/debug/embedding-health
   ```

2. **Run batch embedding generation (if coverage <100%):**
   ```bash
   cd apps/api
   poetry run python scripts/admin/generate_missing_embeddings.py
   ```

3. **Verify fix:**
   - Re-check health endpoint → coverage should be 100%
   - Test semantic search: `POST /api/v1/chat/query` → should return relevant chunks

### Batch Embedding Script

**Script:** `scripts/admin/generate_missing_embeddings.py`

**Usage:**
```bash
cd apps/api
poetry run python scripts/admin/generate_missing_embeddings.py
```

**What it does:**
- Queries documents with `embedding IS NULL` chunks
- Calls `index_chunks()` pipeline (OpenAI embeddings + LangChain vector store)
- Uses **advisory locks PostgreSQL** (`pg_try_advisory_lock`) to coordinate with watcher
- DB-side `hashtext()` for key stability cross-process
- Skips documents locked by concurrent watcher processing

**Expected output:**
```
✅ Processed 190/190 chunks | 2 documents | Coverage: 100.00%
```

### Concurrency Safety

**Story 6.4 AC2.5** implemented PostgreSQL advisory locks to prevent race conditions between:
- **Watcher pipeline** (automatic indexing after ingestion)
- **Batch script** (manual fix for missing embeddings)

**Lock mechanism:**
- **Watcher:** Blocking `pg_advisory_lock(hashtext('docs_ns'), hashtext(document_id))` → waits if batch processing same document
- **Batch:** Non-blocking `pg_try_advisory_lock(...)` → skips if watcher active on document

**Key stability:** Uses DB-side `hashtext()` (NOT Python `hash()`) for consistent lock keys cross-process.

**References:**
- Architecture pattern: `docs/architecture/addendum-asyncpg-database-pattern.md` - Pattern 6
- PostgreSQL docs: https://www.postgresql.org/docs/current/functions-admin.html#FUNCTIONS-ADVISORY-LOCKS

### Alert Thresholds

| Metric | Threshold | Severity | Action |
| --- | --- | --- | --- |
| Embedding coverage | `< 100%` | warning | Run batch script, investigate watcher indexing errors |
| Coverage per document | `< 90%` | critical | Document may have indexing failures, check logs |
| Last indexed timestamp | `> 1 day old` | warning | Watcher may not be running or embedding generation disabled |

### Troubleshooting

**Problem:** Chunks saved but no embeddings  
**Cause:** Watcher indexing disabled or OpenAI API errors  
**Fix:** 
1. Verify `WATCHER_ENABLE_EMBEDDING_SYNC` not set to `false`
2. Check Docker logs: `docker logs fisio-rag-api --tail 100 | grep indexing`
3. Run batch script to backfill missing embeddings

**Problem:** Batch script shows "locked by watcher"  
**Cause:** Watcher actively processing same document  
**Resolution:** This is expected behavior (concurrency safety), script will skip and process on next run

**Problem:** Duplicate chunks after concurrent processing  
**Cause:** Advisory locks not working (key instability)  
**Fix:** Verify DB-side `hashtext()` usage in both watcher and batch script (NOT Python `hash()`)

### Monitoring Integration

**Prometheus metrics (future enhancement):**
```
# Embedding coverage
embedding_coverage_percent{pipeline="watcher"} 100.0
embedding_coverage_percent{pipeline="api"} 100.0

# Chunks without embeddings (alert if >0)
chunks_without_embeddings_total 0
```

**Grafana dashboard suggestions:**
- Time series: embedding coverage over time
- Table: per-document status with warnings
- Alert panel: coverage <100% for >1 hour
