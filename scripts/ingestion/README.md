# Ingestion Scripts

Scripts for ingesting documents into the FisioRAG knowledge base.

## ingest_all_documents.py

**Batch ingestion script** - Recursively scans and ingests all documents from a directory.

### Features
- Recursive directory scanning with configurable patterns
- Rate limiting (10 req/min) with jitter and exponential backoff
- Retry logic for transient errors (network, timeouts, 5xx)
- Resume capability via state file
- Comprehensive reporting (Markdown, JSON, CSV)
- Preflight environment checks
- Structured JSON logging

### Usage

**Full ingestion:**
```bash
python ingest_all_documents.py
```

**Test run (limited files):**
```bash
python ingest_all_documents.py --limit 3
```

**Custom configuration:**
```bash
python ingest_all_documents.py \
  --root-dir conoscenza/fisioterapia/ \
  --pattern "*.docx" \
  --sleep-seconds 6 \
  --max-retries 5 \
  --report reports/my_ingestion_report
```

**Resume interrupted run:**
```bash
python ingest_all_documents.py --state-file temp/ingestion_state.json
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--root-dir` | `conoscenza/fisioterapia/` | Root directory to scan recursively |
| `--pattern` | `*.docx` | Glob pattern for file selection (*.docx, *.txt, *.md) |
| `--sleep-seconds` | `6.0` | Minimum delay between requests (rate limiting) |
| `--max-retries` | `5` | Maximum retries for transient errors |
| `--limit` | None | Maximum files to process (for testing) |
| `--report` | `reports/batch_ingestion_report.md` | Report output path |
| `--state-file` | `temp/ingestion_state.json` | State file for resume capability |
| `--api-url` | `${API_BASE_URL}/api/v1/admin/knowledge-base/sync-jobs` | API endpoint |
| `--category` | `fisioterapia` | Document category |

### Required Environment Variables

- `OPENAI_API_KEY` - OpenAI API key for embeddings
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_SERVICE_KEY`) - Supabase service role key
- `SUPABASE_JWT_SECRET` - JWT signing secret
- `API_BASE_URL` - (Optional) FisioRAG API base URL (default: http://localhost)

### Output

The script generates three report formats:
- **Markdown**: Human-readable summary with statistics
- **JSON**: Structured data for programmatic processing
- **CSV**: Tabular format for spreadsheet analysis

Reports include:
- Total files processed (success/failed/skipped)
- Total chunks created
- Processing duration and throughput
- Top files by chunk count
- Failed files with error messages

### Examples

**Dry run with 3 files:**
```bash
python ingest_all_documents.py --limit 3 --report reports/test_run
```

**Full ingestion with custom rate limit:**
```bash
python ingest_all_documents.py --sleep-seconds 7
```

**Process only markdown files:**
```bash
python ingest_all_documents.py --pattern "*.md"
```

### Monitoring

**Watch celery worker logs:**
```bash
docker logs fisio-rag-celery-worker -f
```

**Check database:**
```sql
SELECT COUNT(*) FROM document_chunks;
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NULL;
SELECT COUNT(DISTINCT document_id) FROM document_chunks;
```

## ingest_single_document.py

**Single document ingestion** - Ingests a single document file.

### Usage
```bash
python ingest_single_document.py path/to/document.docx
```

### Parameters
- `document_path` - Path to document file
- `--api-url` - API base URL (default: http://localhost)
- `--admin-email` - Admin email for JWT (default: admin@fisiorag.local)

### Required Environment Variables
- `SUPABASE_JWT_SECRET`
- `API_BASE_URL` (optional)

## verify_ingestion.py

**Verification script** - Verifies document ingestion in the database.

### Usage
```bash
python verify_ingestion.py <job_id>
```

### Required Environment Variables
- `DATABASE_URL`

## Testing

### Unit Tests

**Using Poetry (recommended):**
```bash
cd apps/api
poetry run pytest ../../scripts/ingestion/test_ingest_all_documents.py -v
```

**Or with pip/virtualenv:**
```bash
cd scripts
pip install -r requirements.txt
python -m pytest ingestion/test_ingest_all_documents.py -v
```

Tests coverage:
- Preflight environment checks
- Text extraction (docx, txt, md)
- Payload preparation
- Document discovery
- State management
- Report generation
- API retry logic

### Integration Tests

**Using Poetry (recommended):**
```bash
cd apps/api
poetry run python ../../scripts/ingestion/test_integration_batch_ingestion.py
```

**Or directly:**
```bash
cd scripts/ingestion
python test_integration_batch_ingestion.py
```

Integration test validates:
- End-to-end ingestion flow
- API communication
- Rate limiting
- Resume capability
- Report generation
- Database verification

**Prerequisites for integration tests:**
- Running FisioRAG API (`docker-compose up`)
- Valid `.env` configuration
- Test documents in `conoscenza/fisioterapia/`
