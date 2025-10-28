# FisioRAG Operational Scripts

Directory contenente script operativi per amministrazione, ingestion e maintenance.

## Prerequisites

```bash
# Install dependencies
pip install -r scripts/requirements.txt
```

**Environment Variables Required**:
- `SUPABASE_JWT_SECRET` - JWT signing secret (Supabase Dashboard → API Settings)
- `SUPABASE_SERVICE_KEY` - Service role key (Supabase Dashboard → API Settings)
- `OPENAI_API_KEY` - OpenAI API key
- `DATABASE_URL` - PostgreSQL connection URL (optional, for verify_ingestion.py)
- `API_BASE_URL` - FisioRAG API base URL (default: http://localhost)

**Configuration**:
1. Copy `.env.example` to `.env` in project root
2. Fill in actual values for required variables
3. Never commit `.env` file

## Admin Scripts

### Generate Admin JWT Token

Generate temporary JWT token for admin API operations.

```bash
python scripts/admin/generate_jwt.py --email admin@fisiorag.local --expires-days 7
```

**Arguments**:
- `--email`: Admin email for JWT subject (default: from ADMIN_EMAIL env)
- `--expires-days`: Token expiration in days (default: 365)

**Output**: JWT token string + export commands

**Usage**:
```bash
# Generate token
TOKEN=$(python scripts/admin/generate_jwt.py --expires-days 1)

# Use token in API call
curl -X POST http://localhost/api/v1/admin/knowledge-base/sync-jobs \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"document_text": "...", "metadata": {...}}'
```

## Ingestion Scripts

### Ingest Single Document

Ingest a single document into FisioRAG knowledge base.

```bash
python scripts/ingestion/ingest_single_document.py path/to/document.docx
```

**Arguments**:
- `document_path`: Path to document file (.docx, .txt, .md)
- `--api-url`: API base URL (default: http://localhost)
- `--admin-email`: Admin email for JWT (default: from ADMIN_EMAIL env)

**Supported Formats**:
- `.docx` (Microsoft Word)
- `.txt` (plain text)
- `.md` (Markdown)

**Example**:
```bash
python scripts/ingestion/ingest_single_document.py \
  conoscenza/fisioterapia/lombare/1_Radicolopatia_Lombare_COMPLETA.docx
```

**Output**: Job ID + ingestion result

### Verify Ingestion

Verify document ingestion success in database.

```bash
python scripts/ingestion/verify_ingestion.py <job_id>
```

**Arguments**:
- `job_id`: Job ID from ingestion response
- `--database-url`: PostgreSQL connection URL (default: from DATABASE_URL env)

**Example**:
```bash
# Ingest document and capture job_id
RESPONSE=$(python scripts/ingestion/ingest_single_document.py test.docx)
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')

# Verify ingestion
python scripts/ingestion/verify_ingestion.py $JOB_ID
```

**Output**: Document info + chunk count

## Performance Scripts (perf/)

### P95 Latency Testing

Script per misurare latenza p95 su endpoint API critici.

```powershell
# Eseguire test p95 con warmup
.\scripts\perf\run_p95_with_warmup.ps1

# Solo test p95
.\scripts\perf\run_p95.ps1

# Warmup cache classificazione
cd apps/api
poetry run python ../../scripts/perf/warmup_classification_cache.py
```

Report generati in `reports/` con metriche latenza.

### Summarize P95 Results

```powershell
cd apps/api
poetry run python ../../scripts/perf/summarize_p95.py
```

Analizza risultati test e genera summary statistico.

## Validation Scripts (validation/)

Script per verifica configurazione e integrità sistema.

### Validate RAG System

```powershell
cd apps/api
poetry run python ../../scripts/validation/validate_rag_system.py
```

Controlla:
- Environment variables
- Docker services status
- Redis connectivity
- API health
- OpenAI API key validity

### Database Integrity Audit

```powershell
cd apps/api
poetry run python ../../scripts/validation/database_integrity_audit.py
```

Verifica integrità database (chunks NULL, FK violations).

### Chunk Integrity Check

```powershell
.\scripts\validation\run_chunk_integrity_check.ps1
```

Verifica coerenza chunks (embedding, document_id).

Consultare `scripts/validation/README.md` per documentazione completa.

## Security Scripts (security/)

### Secret Scanning

```bash
bash scripts/security/run_secret_scans.sh
```

Scansione repository per secrets/credenziali esposte.

**Nota**: Script Bash, eseguire in WSL o Git Bash su Windows.

## Ops Scripts (ops/)

### Watcher Debug

Script per debugging file watcher ingestion.

```powershell
.\scripts\ops\watcher-debug.ps1
```

Monitora cartella watch/ e traccia eventi ingestion.

## Maintenance Scripts

### Cleanup Test Data

```powershell
cd apps/api
poetry run python ../../scripts/validation/cleanup_test_data.py --confirm
```

Elimina tutti chunks e documenti dal database (operazione irreversibile).

### Generate Missing Embeddings

```powershell
cd apps/api
poetry run python ../../scripts/admin/generate_missing_embeddings.py
```

Rigenera embeddings per chunks con embedding NULL.

## Troubleshooting

### Error: "SUPABASE_JWT_SECRET not found in environment"

**Cause**: `.env` file not found or missing required variable

**Solution**:
1. Create `.env` file in project root
2. Copy content from `.env.example`
3. Fill in actual values from Supabase Dashboard

### Error: "AuthenticationError: Error code: 401"

**Cause**: Invalid OpenAI API key

**Solution**:
1. Verify `OPENAI_API_KEY` in `.env`
2. Check key validity in OpenAI Platform
3. Ensure no trailing spaces in key value

### Error: "ConnectionError: Failed to connect to API"

**Cause**: API server not running or wrong URL

**Solution**:
1. Verify API is running: `docker ps | grep fisio-rag-api`
2. Check API_BASE_URL in `.env` (should be http://localhost if local)
3. Test API health: `curl http://localhost/health`
