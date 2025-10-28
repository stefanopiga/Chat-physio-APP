# Pipeline Ingestion Troubleshooting

**Story 2.5**: Intelligent Document Preprocessing & Pipeline Completion  
**AC9**: Troubleshooting guide per errori comuni pipeline

---

## Problema: Chunks creati ma non embedati

**Sintomi**:
- Script ingestion completa con HTTP 200 OK
- `job_id` ritornato correttamente
- Query DB mostra chunks in `document_chunks` ma colonna `embedding` è NULL
- Chat non funziona: semantic search ritorna zero risultati

**Diagnosi**:

### 1. Verifica Celery worker status

```bash
docker logs fisio-rag-celery-worker
```

**Output atteso**:
```
[INFO] celery@hostname ready.
[INFO] Task kb_indexing_task[...] received
```

**Se worker non running**:
```bash
docker ps | grep celery-worker
# Se non presente:
docker compose up -d celery-worker
```

### 2. Verifica Redis accessibile

```bash
docker exec -it fisio-rag-redis redis-cli PING
```

**Output atteso**: `PONG`

**Se Redis non risponde**:
```bash
docker compose restart redis
docker compose restart celery-worker  # Worker dipende da Redis
```

### 3. Verifica task status

```bash
curl -H "Authorization: Bearer $ADMIN_JWT" \
  http://localhost/api/v1/admin/knowledge-base/sync-jobs/{job_id}
```

**Output atteso**:
```json
{
  "job_id": "uuid-here",
  "status": "SUCCESS",
  "inserted": 121,
  "error": null
}
```

**Status possibili**:
- `PENDING`: Task non ancora processato (worker down o sovraccarico)
- `SUCCESS`: Completato con successo
- `FAILURE`: Errore durante processing (check `error` field)

### 4. Check OpenAI API key validity

```bash
docker logs fisio-rag-api | grep "openai_auth_failed"
```

**Se authentication error presente**:
- Verifica `.env` file: `OPENAI_API_KEY=sk-...`
- Verifica chiave valida su https://platform.openai.com/api-keys
- Restart containers dopo update `.env`:
  ```bash
  docker compose down
  docker compose up -d
  ```

**Soluzioni**:

| Problema | Soluzione | Comando |
|----------|-----------|---------|
| Celery worker non running | Restart worker service | `docker compose up -d celery-worker` |
| OpenAI API key invalida | Update `.env` OPENAI_API_KEY | `docker compose restart api celery-worker` |
| Timeout embedding | Aumentare result_expires | Update `celery_app.py` result_expires |
| Rate limit OpenAI | Wait e retry automatico | Attivo (max 5 tentativi, exponential backoff) |

---

## Problema: Embedding lento (> 5 min per 100 chunks)

**Sintomi**:
- Pipeline completa ma richiede tempo eccessivo
- Timeout frontend durante upload documento

**Diagnosi**:

### 1. Check timing metrics in logs

```bash
docker logs fisio-rag-api | grep "indexing_metrics"
```

**Output esempio**:
```json
{
  "event": "indexing_metrics",
  "timing": {
    "embedding_ms": 45000,
    "supabase_insert_ms": 2000,
    "total_ms": 47000
  }
}
```

**Interpretazione**:
- `embedding_ms > 30000`: Bottleneck OpenAI API
- `supabase_insert_ms > 10000`: Bottleneck Supabase connection
- Check quale phase è lento

### 2. Verifica OpenAI API latency

```bash
curl -w "@curl-format.txt" -o /dev/null -s https://api.openai.com/v1/models
```

**Se latency > 2s**: Possibile congestione OpenAI API o piano free rate-limited

**Soluzioni**:

| Causa | Soluzione | Impact |
|-------|-----------|--------|
| Batch size troppo grande | Ridurre BATCH_SIZE in `indexer.py` (100 → 50) | -50% per batch, +100% batches |
| Rate limiting piano OpenAI | Upgrade piano OpenAI (Tier 1 → Tier 2) | +5x rate limit |
| Latenza OpenAI API alta | Wait e retry, considerare embedding locale | Phase 2 |
| Supabase slow insert | Check Supabase dashboard performance | Verifica piano Supabase |

### 3. Performance targets reference

**Target Story 2.5 (AC8)**:
- Extraction: < 2s per documento 50 pagine PDF
- Classification: < 3s per documento
- Chunking: < 1s per 100 chunks
- **Embedding: < 30s per 100 chunks** ⬅️ bottleneck comune
- Supabase Insert: < 5s per 100 chunks
- **Pipeline Total: < 60s** per documento medio

**Se timing supera targets**: Check logs timing metrics per identificare phase lento.

---

## Problema: Celery task stuck in PENDING

**Sintomi**:
- Task status rimane `PENDING` indefinitamente
- Worker logs non mostrano task received

**Diagnosi**:

```bash
# 1. Check Celery worker logs per exceptions
docker logs fisio-rag-celery-worker --tail=100

# 2. Check Redis connection
docker logs fisio-rag-celery-worker | grep "redis"

# 3. List active Celery workers
docker exec -it fisio-rag-celery-worker celery -A api.celery_app:celery_app inspect active
```

**Cause comuni**:

| Causa | Sintomo | Soluzione |
|-------|---------|-----------|
| Worker non ha dipendenze | `ModuleNotFoundError: langchain` | Rebuild worker: `docker compose build celery-worker` |
| Serialization error | `TypeError: Object of type X is not JSON serializable` | Verifica payload serializable (primitives only) |
| Task routing errato | Task inviato a queue non esistente | Check `celery_app.py` routing config |
| Redis connection lost | `ConnectionError: Error connecting to Redis` | `docker compose restart redis celery-worker` |

**Soluzione generica**:

```bash
# Rebuild Celery worker container con dipendenze aggiornate
docker compose build celery-worker
docker compose up -d celery-worker

# Verify worker registered
docker logs fisio-rag-celery-worker | grep "registered"
# Expected: [tasks]\n  . kb_indexing_task
```

---

## Problema: File extraction fallisce (PDF/DOCX corrotto)

**Sintomi**:
- Extraction step fallisce con exception
- Log mostra: `pdf_extraction_error` o `docx_extraction_error`

**Diagnosi**:

```bash
docker logs fisio-rag-api | grep "extraction_error"
```

**Output esempio**:
```json
{
  "event": "pdf_extraction_error",
  "file": "/path/document.pdf",
  "error": "PDF file is encrypted or corrupted"
}
```

**Soluzioni**:

| Causa | Sintomo | Soluzione |
|-------|---------|-----------|
| PDF encrypted | `PDF file is encrypted` | Rimuovere password PDF prima upload |
| DOCX corrotto | `BadZipFile: File is not a zip file` | Verificare integrità file, ri-salvare da Word |
| Encoding non supportato | `UnicodeDecodeError` | Convertire file in UTF-8 |
| File troppo grande | `MemoryError` | Ridurre dimensione file < 50MB (Phase 2: file size limit) |

**Fallback comportamento**:
- Se extraction fallisce, pipeline usa `document_text` fornito come fallback
- Log warning: `extraction_failed_fallback`
- Processing continua normalmente

---

## Problema: Classification confidence bassa (< 0.5)

**Sintomi**:
- Metadata documento mostra `classification_confidence < 0.5`
- Dominio classificato come `tecnico_generico` (fallback category)

**Diagnosi**:

```bash
docker logs fisio-rag-api | grep "classification_complete"
```

**Output esempio**:
```json
{
  "event": "classification_complete",
  "domain": "tecnico_generico",
  "structure": "TESTO_ACCADEMICO_DENSO",
  "confidence": 0.4,
  "duration_ms": 2500
}
```

**Cause**:
- Documento ambiguo (mix di più domini)
- Testo troppo breve per classification accurata (< 500 caratteri)
- Contenuto non fisioterapico

**Azioni**:
1. **Accept**: Confidence < 0.7 è accettabile per MVP (AC2)
2. **Manual override**: Admin può aggiornare metadata documento manualmente
3. **Phase 2**: Implement classification review UI per admin

---

## Problema: Database NULL embeddings after pipeline success

**Sintomi**:
- Pipeline ritorna `inserted: 121`
- Query DB: `SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL` → count > 0

**Diagnosi**: **CRITICAL BUG** - Indica data integrity issue

```sql
-- Check dettaglio chunks senza embedding
SELECT 
  id, 
  document_id, 
  created_at,
  LENGTH(content) as content_size,
  embedding IS NULL as is_null
FROM document_chunks 
WHERE embedding IS NULL
ORDER BY created_at DESC
LIMIT 10;
```

**Possibili cause**:
1. SupabaseVectorStore.add_texts non ha creato embeddings
2. Batch parziale: alcuni chunks embedati, altri no
3. Transaction rollback durante insert

**Soluzione**:

```bash
# 1. Check logs indexer per errori parziali
docker logs fisio-rag-api | grep "partial_insertion"

# 2. Re-run indexing per documento affetto
# (Feature Story 2.6: Re-indexing endpoint)

# 3. Temporary workaround: Delete e re-upload documento
curl -X DELETE -H "Authorization: Bearer $ADMIN_JWT" \
  http://localhost/api/v1/admin/documents/{document_id}
```

**Prevention**: Story 2.5 AC6 retry logic riduce probabilità rate limit failures.

---

## Problema: Pipeline timeout (> 5 min)

**Sintomi**:
- Frontend mostra timeout error
- Backend pipeline ancora running

**Causa**: Pipeline sincrona per documenti grandi

**Soluzione**:

### Opzione 1: Enable Celery async (RECOMMENDED)

Aggiorna `.env`:
```bash
CELERY_ENABLED=true
```

Restart services:
```bash
docker compose restart api celery-worker
```

**Vantaggi**:
- Pipeline non-blocking
- Frontend può polling status via `/sync-jobs/{job_id}`
- Resilience: task riprende se worker restartato

### Opzione 2: Aumentare timeout frontend

File: `apps/web/src/...` (frontend timeout config)

**Non raccomandato**: Sync pipeline max 5 min è design limit.

---

## Logs Interpretation Guide

### Eventi chiave pipeline (order):

```json
// 1. Pipeline start
{"event": "extraction_complete", "images_count": 5, "tables_count": 2}

// 2. Classification
{"event": "classification_complete", "domain": "fisioterapia_clinica", "confidence": 0.85}

// 3. Chunking
{"event": "chunking_complete", "chunks_count": 121, "strategy": "recursive"}

// 4. Embedding (batch progress)
{"event": "embedding_batch", "batch": 1, "total_batches": 2}
{"event": "embedding_batch_complete", "batch": 1, "embeddings_count": 100}

// 5. Indexing complete
{"event": "indexing_complete", "inserted_count": 121, "timing": {...}}

// 6. Pipeline summary
{"event": "pipeline_complete", "timing": {"total_pipeline_ms": 45000}}
```

### Error events:

```json
// OpenAI auth failed
{"event": "openai_auth_failed", "error": "Incorrect API key"}

// Extraction fallback (non-critical)
{"event": "extraction_failed_fallback", "source_path": "/path/doc.pdf"}

// Supabase insertion rejected (CRITICAL)
{"event": "supabase_insertion_rejected", "error": "No rows added"}

// Pipeline failed (CRITICAL)
{"event": "pipeline_failed", "error": "..."}
```

---

## Quick Diagnostic Commands

```bash
# 1. Check all services status
docker compose ps

# 2. Check API logs recent errors
docker logs fisio-rag-api --tail=50 | grep -i error

# 3. Check Celery worker health
docker exec -it fisio-rag-celery-worker celery -A api.celery_app:celery_app inspect ping

# 4. Check Redis connectivity
docker exec -it fisio-rag-redis redis-cli PING

# 5. Database chunks count
docker exec -it fisio-rag-api psql $DATABASE_URL \
  -c "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL"

# 6. Recent pipeline timing metrics
docker logs fisio-rag-api | grep "pipeline_complete" | tail -5
```

---

## Performance Optimization Checklist

- [ ] Celery worker running (async processing)
- [ ] Redis healthy (< 1s ping latency)
- [ ] OpenAI API key valid (Tier 1+)
- [ ] Batch size ottimizzato (100 chunks)
- [ ] Supabase connection pool sized appropriately
- [ ] Timing metrics monitorate (check logs)
- [ ] Retry logic attivo (tenacity exponential backoff)

---

## Support Resources

**Issue report**: Include nei ticket di support:
1. `docker logs fisio-rag-api | grep "pipeline_complete"` (timing metrics)
2. `docker logs fisio-rag-celery-worker --tail=100` (worker state)
3. Job ID del documento affetto
4. Database query: `SELECT * FROM documents WHERE id = '{job_id}'`

**Architecture docs**: `docs/architecture/sezione-8-epic-2-core-knowledge-pipeline.md`

**Story reference**: `docs/stories/2.5.intelligent-document-preprocessing.md`

