# Manual E2E Validation Checklist - Story 2.6

**Scopo**: Checklist operativa per esecuzione manuale validazione sistema RAG.

**Prerequisiti**:
- Docker Compose running: `docker compose ps` (tutti servizi Up)
- Admin JWT token: Genera con `python scripts/admin/generate_jwt.py --email admin@fisiorag.local --expires-days 1` (copia output)
- Documento test preparato: `conoscenza/fisioterapia/lombare/lombalgia-test.docx`
- Script dependencies: `pip install -r scripts/requirements.txt` (se esegui da host)
- **PowerShell**: Comandi per Windows, usa `;` per separare comandi multipli, non `&&`

## Fase 1: Infrastructure Health

### 1.1 Docker Services Status

- [ ] **API Container** (`fisio-rag-api`)
  - [ ] Status: Up (non Restarting)
  - [ ] Logs clean: `docker logs fisio-rag-api --tail=50` (no errors)
  - [ ] Health endpoint: `curl http://localhost/health` → 200 OK (via Traefik proxy)
  - [ ] Environment vars loaded: check logs per "SUPABASE_URL", "OPENAI_API_KEY"

- [ ] **Celery Worker Container** (`fisio-rag-celery-worker`)
  - [ ] Status: Up
  - [ ] Logs show "ready": `docker logs fisio-rag-celery-worker | grep ready`
  - [ ] Worker registered: logs show "celery@<hostname> ready"
  - [ ] No connection errors: check logs per "redis", "broker"

- [ ] **Redis Container** (`fisio-rag-redis`)
  - [ ] Status: Up
  - [ ] Ping test: `docker exec fisio-rag-redis redis-cli PING` → PONG
  - [ ] Keys accessible: `docker exec fisio-rag-redis redis-cli KEYS '*'` (lista chiavi o vuoto)

### 1.2 Network Connectivity

- [ ] **API → Redis**
  - [ ] Test connection: `docker exec fisio-rag-api python -c "import redis; r=redis.Redis(host='redis', port=6379); print(r.ping())"`
  - [ ] Expected output: `True`
  - [ ] No DNS resolution errors

- [ ] **Celery Worker → Redis**
  - [ ] Verify broker_url in logs: `redis://redis:6379/0`
  - [ ] No connection refused errors

- [ ] **API → Supabase**
  - [ ] Test connection: SQL query via `asyncpg` o health endpoint custom
  - [ ] Verify SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY valid

### 1.3 Environment Variables Audit

- [ ] **API Container** (`docker exec fisio-rag-api env | grep -E "SUPABASE|OPENAI|CELERY|JWT"`)
  - [ ] `SUPABASE_URL`: ✓ presente, formato https://xxx.supabase.co
  - [ ] `SUPABASE_SERVICE_ROLE_KEY`: ✓ presente, non placeholder
  - [ ] `SUPABASE_ANON_KEY`: ✓ presente (se usato)
  - [ ] `OPENAI_API_KEY`: ✓ presente, sk-xxx formato
  - [ ] `CELERY_ENABLED`: ✓ "true" (o "false" se sync mode)
  - [ ] `CELERY_BROKER_URL`: ✓ redis://redis:6379/0
  - [ ] `SUPABASE_JWT_SECRET`: ✓ presente (per verifica token)

- [ ] **Celery Worker Container** (idem)
  - [ ] Stesse variabili API + CELERY_* specifiche

## Fase 2: Database Integrity Pre-Test

### 2.1 Database Schema Validation

- [ ] **Table documents exists**
  - Query: `SELECT COUNT(*) FROM documents;`
  - Expected: table exists, count ≥ 0

- [ ] **Table document_chunks exists**
  - Query: `SELECT COUNT(*) FROM document_chunks;`
  - Expected: table exists, count ≥ 0

- [ ] **pgvector extension enabled**
  - Query: `SELECT * FROM pg_extension WHERE extname = 'vector';`
  - Expected: 1 row (extension installed)

- [ ] **Embedding column type correct**
  - Query: `SELECT data_type FROM information_schema.columns WHERE table_name = 'document_chunks' AND column_name = 'embedding';`
  - Expected: `USER-DEFINED` (vector type)

- [ ] **Index on embedding exists**
  - Query: `SELECT indexname FROM pg_indexes WHERE tablename = 'document_chunks' AND indexdef LIKE '%embedding%';`
  - Expected: almeno 1 indice (ivfflat o hnsw)

### 2.2 Baseline Data State

- [ ] **Count existing documents**
  - Query: `SELECT COUNT(*), status FROM documents GROUP BY status;`
  - Note count: _____ completed, _____ processing, _____ error

- [ ] **Count existing chunks**
  - Query: `SELECT COUNT(*) FROM document_chunks;`
  - Note count: _____ chunks totali

- [ ] **Check NULL embeddings (known issue)**
  - Query: `SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;`
  - Note count: _____ chunks con embedding NULL
  - **Expected after fix: 0**

## Fase 2-bis: Database Cleanup (Fresh Test)

**Scopo**: Eliminare tutti chunks e documenti esistenti per test pipeline fresh.

### 2-bis.1 Cleanup Execution

**Comando** (PowerShell):
```powershell
# Opzione A: Con Poetry (da apps/api)
cd apps/api
poetry run python ../../scripts/validation/cleanup_test_data.py --confirm --verbose

# Opzione B: Python standalone (da project root)
python scripts/validation/cleanup_test_data.py --confirm --verbose
```

**Checklist**:
- [ ] Script eseguito senza errori
- [ ] Output mostra conteggi:
  - [ ] `chunks_deleted`: N
  - [ ] `documents_deleted`: M
- [ ] Messaggio: "✅ Cleanup completato"

### 2-bis.2 Verification Post-Cleanup

**SQL Query** (via Supabase Studio o script):
```sql
SELECT COUNT(*) as total_chunks FROM document_chunks;
-- Expected: 0

SELECT COUNT(*) as total_docs FROM documents;
-- Expected: 0
```

**Checklist**:
- [ ] `total_chunks` = **0**
- [ ] `total_docs` = **0**
- [ ] Database vuoto, ready per ingestion fresh

**Alternative** (Python one-liner):
```powershell
python -c "import psycopg2; import os; from dotenv import load_dotenv; from pathlib import Path; load_dotenv(Path('.env')); conn = psycopg2.connect(os.getenv('DATABASE_URL')); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM document_chunks'); print(f'Chunks: {cur.fetchone()[0]}'); cur.execute('SELECT COUNT(*) FROM documents'); print(f'Docs: {cur.fetchone()[0]}'); conn.close()"
```

---

## Fase 3: Preprocessing LLM Pipeline Validation

**Scopo**: Verificare flusso Extraction → Classification LLM → Intelligent Chunking.

### 3.0 LLM Preprocessing End-to-End Test

**Prerequisito**: OPENAI_API_KEY valida in `.env` file root (model: gpt-5-nano)

**Materiale Test**:
- Doc A: Testo accademico (es. `conoscenza/fisioterapia/lombare/lombalgia-anatomia.docx`)
- Doc B: Paper scientifico (es. documento con tabelle dati, references)
- Doc C: Documento tabellare (es. protocolli esercizi)

**Test Python REPL** (da apps/api con Poetry):
```powershell
cd apps/api
poetry run python
```

```python
from pathlib import Path
from api.knowledge_base.extractors import DocumentExtractor
from api.knowledge_base.classifier import classify_content_enhanced
from api.ingestion.chunk_router import ChunkRouter
from api.ingestion.models import ClassificazioneOutput

# Doc A: Testo Accademico
doc_path = Path("../../conoscenza/fisioterapia/lombare/test-accademico.docx")
extractor = DocumentExtractor()
extraction = extractor.extract(doc_path)
text = extraction["text"]
metadata = extraction["metadata"]

print(f"Extracted: {len(text)} chars, images={metadata.get('images_count', 0)}, tables={metadata.get('tables_count', 0)}")

# Classification LLM
classification = classify_content_enhanced(text, metadata)
print(f"Domain: {classification.domain.value}")
print(f"Structure: {classification.structure_type.value}")
print(f"Confidence: {classification.confidence}")
print(f"Reasoning: {classification.reasoning[:100]}...")

# Intelligent Chunking
router = ChunkRouter()
classification_for_chunking = ClassificazioneOutput(
    classificazione=classification.structure_type,
    motivazione=classification.reasoning,
    confidenza=classification.confidence
)
chunks_result = router.route(text, classification_for_chunking)
print(f"Strategy: {chunks_result.strategy_name}")
print(f"Chunks: {len(chunks_result.chunks)}")
print(f"Sample chunk (first 200 chars): {chunks_result.chunks[0][:200]}")
```

**Checklist Doc A (Testo Accademico)**:
- [ ] Extraction: `text` non vuoto, length > 100 chars
- [ ] Classification:
  - [ ] `domain`: fisioterapia_clinica, anatomia, patologia (appropriato)
  - [ ] `structure_type`: **TESTO_ACCADEMICO_DENSO**
  - [ ] `confidence`: >= 0.85
  - [ ] `reasoning`: motivazione sensata
- [ ] Chunking:
  - [ ] `strategy_name`: **recursive** (o fallback::recursive)
  - [ ] `chunks`: > 0, count ragionevole (es. 3-10 per doc ~500 words)
  - [ ] Sample chunk: testo completo, no troncamenti strani
- [ ] LLM response time: < 5s
- [ ] No errors: RateLimitError, API key invalid

**Checklist Doc B (Paper Scientifico con Tabelle)**:
- [ ] Extraction: `tables_count` > 0
- [ ] Classification:
  - [ ] `domain`: **evidence_based** (o appropriato)
  - [ ] `structure_type`: **PAPER_SCIENTIFICO_MISTO**
  - [ ] `confidence`: >= 0.85
- [ ] Chunking:
  - [ ] `strategy_name`: **tabular**
  - [ ] Chunks preservano struttura tabellare

**Checklist Doc C (Documento Tabellare)**:
- [ ] Extraction: `tables_count` > 0
- [ ] Classification:
  - [ ] `structure_type`: **DOCUMENTO_TABELLARE**
  - [ ] `confidence`: >= 0.85
- [ ] Chunking:
  - [ ] `strategy_name`: **tabular**

**Verifiche Generali**:
- [ ] ContentDomain: 8 categorie mappate correttamente
- [ ] DocumentStructureCategory: 3 categorie + fallback
- [ ] ChunkingStrategy routing:
  - TESTO_ACCADEMICO_DENSO → recursive
  - PAPER_SCIENTIFICO_MISTO → tabular
  - DOCUMENTO_TABELLARE → tabular
  - Fallback (confidence < 0.85) → fallback::recursive
- [ ] No fallback indesiderato (confidence sempre >= 0.85 per doc validi)

---

## Fase 4: Pipeline API End-to-End Execution

### 4.1 Document Upload & Ingestion (via API)

**Comando** (PowerShell):
```powershell
# Sostituisci <YOUR_JWT_TOKEN> con token generato da prerequisiti
curl -X POST http://localhost/api/v1/admin/knowledge-base/sync-jobs `
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{
    \"document_text\": \"Lombalgia acuta: diagnosi differenziale. Il trattamento prevede mobilizzazione vertebrale L4-L5 con tecnica Maitland grado II-III. Controindicazioni: osteoporosi severa, fratture recenti.\",
    \"metadata\": {
      \"document_name\": \"test-lombalgia-validation.txt\",
      \"source_path\": \"/app/conoscenza/fisioterapia/lombare/test.txt\"
    }
  }' | ConvertFrom-Json
```

**Note**: Sostituire `<YOUR_JWT_TOKEN>` con token JWT generato in prerequisiti. Output JSON verrà parsato da ConvertFrom-Json.

**Note Preprocessing**: API esegue automaticamente:
1. Extraction (se source_path fornito)
2. Classification LLM (gpt-5-nano)
3. Intelligent Chunking (basato su classification)
4. Embedding + Indexing

**Checklist**:
- [ ] HTTP Status: **200 OK** (no 4xx, 5xx)
- [ ] Response JSON:
  - [ ] `job_id`: presente (UUID format)
  - [ ] `inserted`: > 0 (almeno 1 chunk ingerito)
  - [ ] `timing`: presente (extraction_ms, classification_ms, chunking_ms, embedding_ms)
- [ ] Note job_id: `____________________________________`
- [ ] **Logs API preprocessing** (`docker logs fisio-rag-api --tail 50`):
  - [ ] `extraction_complete`: images_count, tables_count, duration_ms
  - [ ] `classification_complete`: domain, structure, confidence (>= 0.85), duration_ms
  - [ ] `chunking_complete`: chunks_count (> 0), strategy (recursive/tabular), duration_ms
  - [ ] No errors: RateLimitError, OpenAI API invalid key

### 4.2 Pipeline Logs Analysis

**Comando**: `docker logs -f fisio-rag-api | grep -E "extraction|classification|chunking|embedding|indexing"`

**Checklist eventi logged**:
- [ ] **Event: extraction_complete** (se source_path fornito)
  - [ ] `images_count`: numero
  - [ ] `tables_count`: numero
  - [ ] `duration_ms`: < 2000ms per documento piccolo

- [ ] **Event: classification_complete**
  - [ ] `domain`: uno dei domini fisioterapici (es. "fisioterapia_clinica")
  - [ ] `structure`: es. "TESTO_ACCADEMICO_DENSO"
  - [ ] `confidence`: >= 0.7
  - [ ] `duration_ms`: < 3000ms

- [ ] **Event: chunking_complete**
  - [ ] `chunks_count`: > 0 (es. 1-5 per testo breve)
  - [ ] `strategy`: es. "recursive" o "by_title"
  - [ ] `duration_ms`: < 1000ms

- [ ] **Event: indexing_start** (o embedding_start)
  - [ ] `chunks_count`: match con chunking

- [ ] **Event: indexing_complete** (o pipeline_complete)
  - [ ] `inserted`: > 0 (match chunks_count)
  - [ ] `timing.embedding_ms`: presente
  - [ ] `timing.supabase_insert_ms`: presente
  - [ ] `timing.total_pipeline_ms`: < 60000ms (target < 60s)

**Se Celery async**:
- [ ] Celery logs: `docker logs -f fisio-rag-celery-worker`
  - [ ] Task received: `kb_indexing_task`
  - [ ] Task started
  - [ ] Task succeeded (no exceptions)

### 3.3 Database Post-Ingestion Validation

**Attendi**: 5-10 secondi per async completion (se Celery)

**Query 1: Document created**
```sql
SELECT id, file_name, status, chunking_strategy, created_at, metadata
FROM documents
WHERE id = '<job_id_from_3.1>'::uuid;
```
- [ ] 1 row returned
- [ ] `status`: "completed" (non "processing", "error")
- [ ] `chunking_strategy`: presente (es. "recursive")
- [ ] `metadata`: JSON con domain, structure_type

**Query 2: Chunks created**
```sql
SELECT id, content, embedding, metadata
FROM document_chunks
WHERE document_id = '<job_id_from_3.1>'::uuid;
```
- [ ] N rows (N = chunks_count da logs)
- [ ] `content`: non NULL, testo sensato
- [ ] **`embedding`: NOT NULL** ← **CRITICAL CHECK**
- [ ] `metadata`: JSON con document_name, document_id

**Query 3: Embedding dimension validation**
```sql
SELECT id, vector_dims(embedding) as dims
FROM document_chunks
WHERE document_id = '<job_id_from_3.1>'::uuid
LIMIT 1;
```
- [ ] `dims`: **1536** (text-embedding-3-small) o **3072** (text-embedding-3-large)
- [ ] Se NULL: **CRITICAL FAILURE** → root cause investigation

## Fase 4: Semantic Search Validation

### 4.1 Search Endpoint Test

**Prerequisito**: documento ingerito (3.3 validation passed)

**Comando** (PowerShell):
```powershell
# Sostituisci <YOUR_JWT_TOKEN> con token generato
curl -X POST http://localhost/api/v1/rag/search `
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{
    \"query\": \"trattamento lombalgia\",
    \"match_count\": 5,
    \"match_threshold\": 0.0
  }' | ConvertFrom-Json
```

**Checklist**:
- [ ] HTTP Status: **200 OK**
- [ ] Response JSON:
  - [ ] `results`: array presente
  - [ ] Array length: > 0 (almeno 1 risultato)
- [ ] Per ogni result:
  - [ ] `content`: testo chunk presente
  - [ ] `score`: numero > 0 (es. 0.75-0.95 per match forte)
  - [ ] `metadata`: oggetto con `document_id`, `document_name`
- [ ] **Validation semantica**:
  - [ ] Top result contiene keyword rilevanti: "lombalgia", "trattamento", "vertebrale"
  - [ ] Score top result > 0.7 (buona relevanza)

**Se results vuoto**:
- [ ] Investigare: embedding query generato?
- [ ] Check pgvector similarity: query manuale DB
- [ ] Verify match_threshold non troppo alto

### 4.2 Search Performance

- [ ] Response time: **< 500ms** per 5 results
- [ ] Logs API: `docker logs fisio-rag-api | grep search`
  - [ ] `event: semantic_search_start`
  - [ ] `event: semantic_search_complete`
  - [ ] `duration_ms`: < 500

## Fase 5: Chat RAG Validation

### 5.1 Chat Endpoint Test

**Prerequisito**: semantic search funzionante (4.1 passed)

**Comando** (PowerShell):
```powershell
# Sostituisci <YOUR_JWT_TOKEN> con token generato
curl -X POST http://localhost/api/v1/rag/chat `
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" `
  -H "Content-Type: application/json" `
  -d '{
    \"query\": \"Quali tecniche sono indicate per lombalgia acuta?\",
    \"match_count\": 8
  }' | ConvertFrom-Json
```

**Checklist**:
- [ ] HTTP Status: **200 OK**
- [ ] Response JSON:
  - [ ] `answer`: stringa presente, non vuota
  - [ ] `context_chunks`: array presente (chunks retrieved)
  - [ ] `sources`: array presente (se Story 3.4 implementata)

- [ ] **Content validation**:
  - [ ] Answer menziona "mobilizzazione vertebrale" (info da documento test)
  - [ ] Answer menziona "Maitland" o "L4-L5" (dettagli tecnici)
  - [ ] Answer NON generica (es. non solo "consultare un fisioterapista")
  - [ ] Answer coerente con context_chunks

- [ ] **Context chunks**:
  - [ ] Array length: > 0 (almeno 1 chunk)
  - [ ] Chunks contengono testo rilevante da documento test

**Se answer generica o incoerente**:
- [ ] Check logs: LLM prompt include context chunks?
- [ ] Verify OpenAI API call success
- [ ] Check model used: gpt-3.5-turbo vs gpt-4 (quality diff)

### 5.2 Chat Performance

- [ ] Response time: **< 5s** (dipende da OpenAI API)
- [ ] Logs API: `duration_ms` per chat endpoint

## Fase 6: Issue Reproduction Attempts

### 6.1 Tentativo Riproduzione "121 Chunks NULL Embeddings"

**Scenario**: ingestione multipla rapida per stressare sistema

**Comando** (PowerShell - rapida successione < 10s intervallo):

```powershell
# Sostituisci <YOUR_JWT_TOKEN> con token generato
# Esegui 3 richieste in rapida successione (background jobs)
1..3 | ForEach-Object {
  $i = $_
  Start-Job -ScriptBlock {
    param($index, $token)
    curl -X POST http://localhost/api/v1/admin/knowledge-base/sync-jobs `
      -H "Authorization: Bearer $token" `
      -H "Content-Type: application/json" `
      -d "{`\"document_text`\": `\"Test doc $index contenuto lombalgia`\", `\"metadata`\": {`\"document_name`\": `\"test-$index.txt`\"}}"
  } -ArgumentList $i, "<YOUR_JWT_TOKEN>"
}

# Attendi completion
Get-Job | Wait-Job
Get-Job | Receive-Job
```

**Checklist**:
- [ ] Tutti 3 job_id ritornati
- [ ] Attendi 30s per completion
- [ ] Query DB:
  ```sql
  SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL AND created_at > NOW() - INTERVAL '1 minute';
  ```
- [ ] **Expected: 0** (retry logic previene NULL)
- [ ] Se > 0: **ISSUE RIPRODUCIBILE** → root cause investigation

### 6.2 Rate Limiting Test (OpenAI)

**Scenario**: batch grande per triggerare rate limit

**Note**: Richiede documento grande (100+ chunks) o batch artificiale

**Checklist**:
- [ ] Logs mostrano retry attempts: `grep "RateLimitError" logs`
- [ ] Retry logic attivo: exponential backoff logged
- [ ] Final success: embedding completato dopo retry
- [ ] Se fallisce dopo max retries: **EXPECTED** (rate limit policy)

## Fase 7: Regression Validation

### 7.1 Existing Stories Still Working

- [ ] **Story 3.1**: Semantic search endpoint (validated in Fase 4)
- [ ] **Story 3.2**: Chat RAG endpoint (validated in Fase 5)
- [ ] **Story 3.3**: Frontend chat integration (se testable via UI)
- [ ] **Story 3.4**: Source visualization (check response sources field)

### 7.2 Backward Compatibility

- [ ] API endpoints non breaking changes
- [ ] Database schema unchanged (no ALTER TABLE mancanti)
- [ ] Existing documents still queryable

## Summary & Sign-Off

### Issues Found

| Severity | Component | Issue | Impact | AC Failed |
|---|---|---|---|---|
| P0 | | | | |
| P1 | | | | |
| P2 | | | | |

### Validation Results

| AC # | Description | Status | Notes |
|---|---|---|---|
| AC1 | Environment validation | ☐ PASS ☐ FAIL | |
| AC2 | Service health checks | ☐ PASS ☐ FAIL | |
| AC3 | Celery operational | ☐ PASS ☐ FAIL | |
| AC4 | Pipeline step-by-step | ☐ PASS ☐ FAIL | |
| AC5 | Database integrity | ☐ PASS ☐ FAIL | |
| AC6 | Semantic search | ☐ PASS ☐ FAIL | |
| AC7 | Chat RAG | ☐ PASS ☐ FAIL | |
| AC8 | Config gap analysis | ☐ PASS ☐ FAIL | |
| AC9 | Test coverage gap | ☐ PASS ☐ FAIL | |
| AC10 | Fix backlog created | ☐ PASS ☐ FAIL | |

### Overall Assessment

- **Total ACs**: 10
- **PASS**: ___ / 10
- **FAIL**: ___ / 10
- **Story Status**: ☐ PASS ☐ PARTIAL ☐ FAIL

**Validator**: _______________  
**Date**: _______________  
**Next Actions**: _______________

