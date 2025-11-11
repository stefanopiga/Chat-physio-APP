# Chat-physio-APP Operational Scripts

Directory contenente script operativi per amministrazione, ingestion, performance testing, validation e security.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables Setup](#environment-variables-setup)
- [Safety Checklist](#safety-checklist)
- [Admin Scripts](#admin-scripts)
- [Ingestion Scripts](#ingestion-scripts)
- [Performance Scripts](#performance-scripts)
- [Validation Scripts](#validation-scripts)
- [Security Scripts](#security-scripts)
- [Operations Scripts](#operations-scripts)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

#### 1. Python 3.11+
Verify installation:
```cmd
python --version
```

Install from: https://www.python.org/downloads/

**Windows Note:** Durante installazione, selezionare "Add Python to PATH"

#### 2. Poetry 1.6+ (Python dependency manager)
Verify installation:
```cmd
poetry --version
```

Install (PowerShell):
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

**PATH Configuration Windows:**
Aggiungi `%APPDATA%\Python\Scripts` a variabili ambiente PATH se Poetry non trovato dopo installazione.

#### 3. Docker Desktop 4.x+
Verify installation:
```cmd
docker --version
```

Install from: https://www.docker.com/products/docker-desktop

**Windows Note:** Docker Desktop richiede WSL 2 backend. Segui wizard installazione per configurazione automatica.

#### 4. pnpm 8+ (Optional, for frontend scripts)
Verify installation:
```cmd
pnpm --version
```

Install:
```cmd
npm install -g pnpm
```

### Additional Tools (Optional)

- **Git Bash** o **WSL 2**: Required per script Bash-only (security scanning)
- **curl**: Nativo Windows 10 (build 1803+) e Windows 11. Verify: `curl --version`

---

## Environment Variables Setup

### Required Variables by Script Category

| Script Category | Required Environment Variables |
|-----------------|-------------------------------|
| **Admin** (`admin/`) | `SUPABASE_JWT_SECRET`, `ADMIN_EMAIL` |
| **Ingestion** (`ingestion/`) | `OPENAI_API_KEY`, `API_BASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_URL` |
| **Validation** (`validation/`) | `DATABASE_URL`, `REDIS_HOST`, `SUPABASE_URL` |
| **Performance** (`perf/`) | `API_BASE_URL` |

### Configuration Steps

1. Copy `.env.example` to `.env` in project root
2. Fill in values from Supabase Dashboard and OpenAI Platform
3. Never commit `.env` file to version control

**Detailed Documentation:**
- `.env.example` - Template environment variables
- `ISTRUZIONI-USO-VARIABILI-AMBIENTE.md` - Complete env vars documentation

### Example .env Configuration

```bash
# Example .env for development - USE PLACEHOLDERS ONLY
# Replace with real values locally - NEVER commit real secrets

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=***REDACTED***
SUPABASE_JWT_SECRET=***REDACTED***

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-***YOUR_KEY_HERE***

# API Configuration
API_BASE_URL=http://localhost
ADMIN_EMAIL=admin@fisiorag.local

# Database (Optional - for verification scripts)
DATABASE_URL=postgresql://postgres:***PASSWORD***@localhost:5432/postgres

# Redis (Optional - for validation scripts)
REDIS_HOST=localhost
REDIS_PORT=6379
```

> **Security Warning**
> 
> **NEVER commit real secrets to version control.**
> - Use placeholders in documentation (e.g., `***REDACTED***`, `***YOUR_KEY_HERE***`)
> - Never display real tokens/credentials in screenshots or terminal captures
> - Run secret scanning regularly: `bash scripts/security/run_secret_scans.sh` (WSL/Git Bash required on Windows)
> - Review `.gitignore` to ensure `.env` is excluded

---

## Safety Checklist

Before executing any script, verify:

- [ ] Environment variables point to correct resources (test/dev/production)
- [ ] Never run data-mutating scripts against production databases
- [ ] Use secret placeholders in documentation and examples
- [ ] Prefer per-session execution policy bypass (PowerShell security)
- [ ] Admin rights required ONLY when explicitly needed (scoped operations)
- [ ] Docker Desktop running for scripts requiring database/Redis services

---

## Admin Scripts

Scripts per operazioni amministrative (JWT generation, embeddings management).

### Generate Admin JWT Token

Generate temporary JWT token per admin API operations.

**Location:** `scripts/admin/generate_jwt.py`

**Usage (cmd):**
```cmd
cd apps\api
poetry run python ..\..\scripts\admin\generate_jwt.py --email admin@fisiorag.local --expires-days 7
```

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/admin/generate_jwt.py --email admin@fisiorag.local --expires-days 7
```

**Arguments:**
- `--email`: Admin email for JWT subject (default: from `ADMIN_EMAIL` env var)
- `--expires-days`: Token expiration in days (default: 365)

**Required Environment Variables:**
- `SUPABASE_JWT_SECRET`
- `ADMIN_EMAIL` (optional if provided via --email)

**Output:** JWT token string + export commands

**Example Workflow (PowerShell):**
```powershell
# Step 1: Generate token
cd apps/api
$token = (poetry run python ../../scripts/admin/generate_jwt.py --expires-days 1) | Select-Object -Last 1

# Step 2: Use token in API call
curl -X POST http://localhost/api/v1/admin/knowledge-base/sync-jobs `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d '{\"document_text\": \"...\", \"metadata\": {}}'
```

**Expected Output:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbkBmaXNpb3JhZy5sb2NhbCIsImV4cCI6MTczMTI1OTIwMH0.signature
```

---

### Generate Missing Embeddings

Rigenera embeddings per chunks con embedding NULL nel database.

**Location:** `scripts/admin/generate_missing_embeddings.py`

> **Data Mutation Warning - Test Environment Only**
> 
> This script modifies database content (updates embeddings). Use ONLY in test/development environments.
> Verify `DATABASE_URL` points to non-production database before execution.

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/admin/generate_missing_embeddings.py
```

**Required Environment Variables:**
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

**Output:** Count of embeddings generated + processing time

---

## Ingestion Scripts

Scripts per ingestione documenti nella knowledge base FisioRAG.

### Ingest All Documents (Batch Ingestion)

Batch ingestion script - Recursively scans and ingests all documents from directory.

**Location:** `scripts/ingestion/ingest_all_documents.py`

**Features:**
- Recursive directory scanning with configurable patterns
- Rate limiting (10 req/min) with jitter and exponential backoff
- Retry logic for transient errors (network, timeouts, 5xx)
- Resume capability via state file
- Comprehensive reporting (Markdown, JSON, CSV)
- Preflight environment checks
- Structured JSON logging

**Usage (PowerShell):**
```powershell
# Full ingestion
cd apps/api
poetry run python ../../scripts/ingestion/ingest_all_documents.py

# Test run (limited files)
poetry run python ../../scripts/ingestion/ingest_all_documents.py --limit 3

# Custom configuration
poetry run python ../../scripts/ingestion/ingest_all_documents.py `
  --root-dir conoscenza/fisioterapia/ `
  --pattern "*.docx" `
  --sleep-seconds 6 `
  --max-retries 5 `
  --report ../../reports/my_ingestion_report

# Resume interrupted run
poetry run python ../../scripts/ingestion/ingest_all_documents.py --state-file temp/ingestion_state.json
```

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--root-dir` | `conoscenza/fisioterapia/` | Root directory to scan recursively |
| `--pattern` | `*.docx` | Glob pattern for file selection |
| `--sleep-seconds` | `6.0` | Minimum delay between requests (rate limiting) |
| `--max-retries` | `5` | Maximum retries for transient errors |
| `--limit` | None | Maximum files to process (for testing) |
| `--report` | `reports/batch_ingestion_report.md` | Report output path |
| `--state-file` | `temp/ingestion_state.json` | State file for resume capability |
| `--api-url` | `${API_BASE_URL}/api/v1/admin/knowledge-base/sync-jobs` | API endpoint |
| `--category` | `fisioterapia` | Document category |

**Required Environment Variables:**
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_JWT_SECRET`
- `API_BASE_URL` (optional, default: http://localhost)

**Output:** Three report formats (Markdown, JSON, CSV) with statistics:
- Total files processed (success/failed/skipped)
- Total chunks created
- Processing duration and throughput
- Top files by chunk count
- Failed files with error messages

**Example Output:**
```
Processing: conoscenza/fisioterapia/lombare/documento.docx
✓ Success: 45 chunks created (job_id: abc123)
Processing: conoscenza/fisioterapia/cervicale/documento2.docx
✓ Success: 32 chunks created (job_id: def456)

Summary:
- Files processed: 2/2
- Total chunks: 77
- Duration: 45.2s
- Throughput: 2.7 files/min
```

**Monitoring:**
```powershell
# Watch celery worker logs
docker logs fisio-rag-celery-worker -f

# Check database
docker exec fisio-rag-postgres psql -U postgres -d postgres -c "SELECT COUNT(*) FROM document_chunks;"
```

---

### Ingest Single Document

Single document ingestion - Ingests one document file.

**Location:** `scripts/ingestion/ingest_single_document.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/ingestion/ingest_single_document.py ../../conoscenza/fisioterapia/lombare/documento.docx
```

**Arguments:**
- `document_path`: Path to document file (.docx, .txt, .md)
- `--api-url`: API base URL (default: http://localhost)
- `--admin-email`: Admin email for JWT (default: admin@fisiorag.local)

**Supported Formats:**
- `.docx` (Microsoft Word)
- `.txt` (plain text)
- `.md` (Markdown)

**Required Environment Variables:**
- `SUPABASE_JWT_SECRET`
- `API_BASE_URL` (optional)

**Output:** Job ID + ingestion result

**Example Output:**
```json
{
  "job_id": "abc123-def456-789",
  "status": "success",
  "chunks_created": 45,
  "document_path": "conoscenza/fisioterapia/lombare/documento.docx"
}
```

---

### Verify Ingestion

Verify document ingestion success in database.

**Location:** `scripts/ingestion/verify_ingestion.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/ingestion/verify_ingestion.py abc123-def456-789
```

**Arguments:**
- `job_id`: Job ID from ingestion response
- `--database-url`: PostgreSQL connection URL (default: from `DATABASE_URL` env var)

**Required Environment Variables:**
- `DATABASE_URL`

**Example Workflow (PowerShell):**
```powershell
# Step 1: Ingest document and capture output
cd apps/api
$response = poetry run python ../../scripts/ingestion/ingest_single_document.py ../../test.docx | ConvertFrom-Json

# Step 2: Extract job_id
$job_id = $response.job_id

# Step 3: Verify ingestion
poetry run python ../../scripts/ingestion/verify_ingestion.py $job_id
```

**Output:** Document info + chunk count

**Example Output:**
```
Document ID: doc_12345
Chunks count: 45
Chunks with embeddings: 45
Status: ✓ All chunks processed successfully
```

---

## Performance Scripts

Scripts per performance testing e latency measurement.

### P95 Latency Testing

Script per misurare latenza p95 su endpoint API critici.

**Location:** `scripts/perf/run_p95_with_warmup.ps1`, `scripts/perf/run_p95.ps1`

**Platform Requirement:** Windows PowerShell 5.1+

**Usage (PowerShell):**
```powershell
# Complete test with warmup
powershell -ExecutionPolicy Bypass -File .\scripts\perf\run_p95_with_warmup.ps1

# P95 test only
powershell -ExecutionPolicy Bypass -File .\scripts\perf\run_p95.ps1
```

**Note:** Script usa per-session ExecutionPolicy Bypass (nessuna modifica permanente al sistema).

**Required Environment Variables:**
- `API_BASE_URL`

**Output:** Report generati in `reports/` directory con metriche latenza (JSON format)

**Example Output:**
```
P95 Latency Results:
- /api/v1/chat: 245ms
- /api/v1/search: 189ms
- /health: 12ms
```

---

### Warmup Classification Cache

Preriscalda cache classificazione query per test performance.

**Location:** `scripts/perf/warmup_classification_cache.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/perf/warmup_classification_cache.py
```

**Required Environment Variables:**
- `API_BASE_URL`
- `REDIS_HOST`

**Output:** Cache warmup status + query count

---

### Summarize P95 Results

Analizza risultati test p95 e genera summary statistico.

**Location:** `scripts/perf/summarize_p95.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/perf/summarize_p95.py
```

**Output:** Statistical summary di tutti report p95 in `reports/` directory

---

### P95 Local Test (Node.js)

Node.js-based performance test script.

**Location:** `scripts/perf/p95_local_test.js`

**Platform Requirement:** Node.js 18+ required

**Usage (cmd):**
```cmd
node scripts\perf\p95_local_test.js
```

**Required Environment Variables:**
- `API_BASE_URL`

---

## Validation Scripts

Scripts per verifica configurazione e integrità sistema RAG.

### Validate RAG System

Script principale per validation automatizzata infrastructure e configurazioni.

**Location:** `scripts/validation/validate_rag_system.py`

**Checks eseguiti:**
- Environment variables (SUPABASE_URL, OPENAI_API_KEY, etc.)
- Docker services status (api, celery-worker, redis)
- Redis connectivity
- API health endpoint
- OpenAI API key validity

**Usage (PowerShell):**
```powershell
# Basic validation
cd apps/api
poetry run python ../../scripts/validation/validate_rag_system.py

# With JSON output and verbose logging
poetry run python ../../scripts/validation/validate_rag_system.py --output ../../reports/validation.json --verbose
```

**Required Environment Variables:**
- `SUPABASE_URL`
- `OPENAI_API_KEY`
- `API_BASE_URL`
- `REDIS_HOST`

**Output:** JSON report con validation results

**Exit Codes:**
- `0`: PASS (tutti check passed)
- `1`: FAIL (almeno un check failed)
- `2`: WARN (warning presenti, nessun failure)

**Example Output:**
```json
{
  "validation_run": {
    "timestamp": "2025-11-11T15:30:00Z",
    "script_version": "1.0.0"
  },
  "summary": {
    "PASS": 5,
    "FAIL": 0,
    "WARN": 0
  },
  "overall_status": "PASS"
}
```

---

### Database Integrity Audit

Verifica integrità database (NULL chunks, foreign key violations).

**Location:** `scripts/validation/database_integrity_audit.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/database_integrity_audit.py
```

**Required Environment Variables:**
- `DATABASE_URL`

**Output:** Integrity check results con count anomalie

---

### Chunk Integrity Check

Verifica coerenza chunks (embedding, document_id, foreign keys).

**Location:** `scripts/validation/run_chunk_integrity_check.ps1`

**Platform Requirement:** Windows PowerShell 5.1+

**Usage (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validation\run_chunk_integrity_check.ps1
```

**Required Environment Variables:**
- `DATABASE_URL`

**Output:** Chunk integrity report

---

### Configuration Gap Analysis

Analizza gap configurazione tra .env e requirements applicazione.

**Location:** `scripts/validation/config_gap_analysis.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/config_gap_analysis.py
```

**Output:** Lista variabili mancanti o non utilizzate

---

### Database Connectivity Test

Test connettività database PostgreSQL.

**Location:** `scripts/validation/database_connectivity_test.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/database_connectivity_test.py
```

**Required Environment Variables:**
- `DATABASE_URL`

**Output:** Connection status + latency

---

### Docker Health Check

Verifica stato servizi Docker (api, celery-worker, redis, postgres).

**Location:** `scripts/validation/docker_health_check.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/docker_health_check.py
```

**Output:** Docker services health status

---

### Environment Audit

Audit completo environment variables configurazione.

**Location:** `scripts/validation/env_audit.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/env_audit.py
```

**Output:** Audit report con variabili presenti, mancanti, deprecate

---

### Generate Test Tokens

Genera JWT tokens per test automatizzati.

**Location:** `scripts/validation/generate_test_tokens.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/generate_test_tokens.py --count 5 --expires-days 1
```

**Required Environment Variables:**
- `SUPABASE_JWT_SECRET`

**Output:** Lista tokens con expiration info

---

### Verify Chunk IDs

Verifica univocità e validità chunk IDs nel database.

**Location:** `scripts/validation/verify_chunk_ids.py`

**Usage (PowerShell):**
```powershell
cd apps/api
poetry run python ../../scripts/validation/verify_chunk_ids.py
```

**Required Environment Variables:**
- `DATABASE_URL`

**Output:** Chunk ID validation report (duplicates, NULL IDs)

---

### Cleanup Test Data

Elimina tutti chunks e documenti dal database (operazione irreversibile).

**Location:** `scripts/validation/cleanup_test_data.py`

> **Data Mutation Warning - Test Environment Only**
> 
> This script performs DELETE operations on database content. Use ONLY in test/development environments.
> Verify `DATABASE_URL` points to non-production database before execution.
> Operation is irreversible - no rollback possible.

**Usage (PowerShell):**
```powershell
# Ensure test environment
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_db"

cd apps/api
poetry run python ../../scripts/validation/cleanup_test_data.py --confirm
```

**Required Environment Variables:**
- `DATABASE_URL` (must point to test database)

**Arguments:**
- `--confirm`: Required flag to confirm deletion (safety mechanism)
- `--verbose`: Detailed logging output

**Output:** Counts before/after cleanup

**Example Output:**
```
Before cleanup: 1234 chunks, 56 documents
Deleting chunks...
Deleting documents...
After cleanup: 0 chunks, 0 documents
✓ Cleanup completed successfully
```

---

## Security Scripts

Scripts per security scanning e vulnerability detection.

### Secret Scanning

Scansione repository per secrets/credenziali esposte (API keys, passwords, tokens).

**Location:** `scripts/security/run_secret_scans.sh`

**Platform Requirement:** Linux/macOS Only - Requires Bash

**Usage (Git Bash on Windows):**
```bash
# From project root
bash scripts/security/run_secret_scans.sh
```

**Windows Users:** Use WSL 2 or Git Bash to execute this script.

**WSL Example:**
```bash
wsl bash scripts/security/run_secret_scans.sh
```

**Output:** Report con secrets rilevati + severity level

**Note:** Eseguire prima di ogni commit/merge per prevenire secret leakage.

---

## Operations Scripts

Scripts per operations e debugging.

### Watcher Debug

Script per debugging file watcher ingestion pipeline.

**Location:** `scripts/ops/watcher-debug.ps1`

**Platform Requirement:** Windows PowerShell 5.1+

**Usage (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\ops\watcher-debug.ps1
```

**Output:** Log eventi file watcher con timestamp e ingestion status

**Note:** Monitora cartella `watch/` per troubleshooting ingestion automatica.

---

## Troubleshooting

### Error: "poetry: command not found"

**Cause:** Poetry non trovato in PATH

**Solution:**
1. Reinstall Poetry con installer ufficiale (vedi Prerequisites)
2. Aggiungere `%APPDATA%\Python\Scripts` a variabili ambiente PATH:
   - Windows: Settings → System → About → Advanced system settings → Environment Variables
   - Aggiungere path a variabile PATH utente
3. Restart terminal/PowerShell
4. Verify: `poetry --version`

**Alternative:** Usa Python virtualenv invece di Poetry:
```cmd
cd apps\api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python ..\..\scripts\admin\generate_jwt.py
```

---

### Error: "Execution policy does not allow running scripts"

**Cause:** PowerShell execution policy restricted (default Windows security)

**SAFE Solution (Recommended):** Per-session bypass (no system changes)
```powershell
# Execute script with per-session Bypass - does NOT modify system security
powershell -ExecutionPolicy Bypass -File .\scripts\perf\run_p95.ps1
```

**Alternative (User-scoped policy):** If per-session not viable
```powershell
# User scope only - does NOT affect system-wide security posture
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Security Warning:** 
- NEVER use Machine scope (`-Scope LocalMachine` or `-Scope Machine`)
- NEVER use Unrestricted policy (security risk)
- Per-session Bypass is safest option (no permanent changes)

**Further Reading:**
- `docs/operations/powershell-execution-policy.md` (if exists)
- Microsoft Docs: https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies

---

### Error: "Docker daemon is not running"

**Cause:** Docker Desktop not started

**Solution:**
1. Launch Docker Desktop from Start Menu
2. Wait for whale icon to be stable in system tray (indicates Docker ready)
3. Verify Docker running:
   ```cmd
   docker ps
   ```
4. If services not running, start them:
   ```cmd
   docker-compose up -d
   ```

**Troubleshooting:**
- Check Docker Desktop settings: WSL 2 backend enabled
- Restart Docker Desktop if stuck
- Check Windows Services: Docker Desktop Service running

**Further Reading:**
- `docs/operations/docker-setup-guide.md` (Docker-specific troubleshooting)

---

### Error: "SUPABASE_JWT_SECRET not found in environment"

**Cause:** `.env` file not found or missing required variable

**Solution:**
1. Create `.env` file in project root (if not exists)
2. Copy content from `.env.example`:
   ```cmd
   copy .env.example .env
   ```
3. Edit `.env` and fill in actual values from Supabase Dashboard:
   - Navigate to: Supabase Project → Settings → API
   - Copy JWT Secret and Service Key
4. Verify `.env` loaded:
   ```powershell
   Get-Content .env | Select-String "SUPABASE_JWT_SECRET"
   ```

**Further Reading:**
- `ISTRUZIONI-USO-VARIABILI-AMBIENTE.md` (complete env vars guide)

---

### Error: "AuthenticationError: Error code: 401" (OpenAI)

**Cause:** Invalid or expired OpenAI API key

**Solution:**
1. Verify `OPENAI_API_KEY` in `.env` file
2. Check key validity on OpenAI Platform: https://platform.openai.com/api-keys
3. Ensure no trailing spaces or quotes around key value:
   ```bash
   # WRONG
   OPENAI_API_KEY="sk-proj-..."
   
   # CORRECT
   OPENAI_API_KEY=sk-proj-...
   ```
4. Regenerate key if expired/revoked
5. Update `.env` with new key

---

### Error: "ConnectionError: Failed to connect to API"

**Cause:** API server not running or wrong URL in configuration

**Solution:**
1. Verify API running:
   ```cmd
   docker ps | findstr fisio-rag-api
   ```
2. Check `API_BASE_URL` in `.env`:
   - Should be `http://localhost` for local development
   - Should NOT include port (Traefik proxy handles routing)
3. Test API health manually:
   ```cmd
   curl http://localhost/health
   ```
4. If API not responding:
   ```cmd
   docker logs fisio-rag-api --tail 50
   docker logs fisio-rag-proxy --tail 50
   ```

**Further Reading:**
- `docs/troubleshooting/api-connectivity-issues.md` (if exists)

---

### Error: "Access is denied" (Windows)

**Cause:** Script requires elevated privileges (Admin rights)

**Solution (Security-Conscious):**

**Step 1:** Check if elevation truly needed
- Most scripts (ingestion, validation, performance) run WITHOUT admin rights
- Admin required ONLY for:
  - System-wide tool installation (Poetry, Docker)
  - Docker service management (rare - usually Docker Desktop handles)
  - Modifying system files outside user directories

**Step 2:** If admin genuinely needed (scoped approach):
1. Launch PowerShell/cmd as Administrator (right-click → "Run as administrator")
2. Navigate to project root
3. Execute ONLY the specific elevated command
4. Exit admin shell immediately after (least privilege principle)

**Step 3:** Prefer user-scoped alternatives when possible:
```powershell
# Example: User-scoped execution policy instead of Machine scope
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# NO Machine scope: Set-ExecutionPolicy -Scope LocalMachine (requires admin)
```

**Security Warning:** 
- Avoid running entire development sessions as Administrator (attack surface risk)
- Scope admin usage to exact steps requiring elevation
- Never run untrusted scripts with admin rights

---

### Error: "Connection refused" (Redis/Database)

**Cause:** Service not accessible from host machine

**Solution:**

**Option A:** Execute script inside Docker container (recommended)
```powershell
# Example: Run validation inside API container
docker exec fisio-rag-api poetry run python /app/scripts/validation/validate_rag_system.py
```

**Option B:** Expose service ports in docker-compose.yml (development only)
```yaml
# Add to redis service in docker-compose.yml
redis:
  ports:
    - "6379:6379"  # Expose Redis port to host
```

Then restart services:
```cmd
docker-compose down
docker-compose up -d
```

**Security Note:** Never expose database/Redis ports in production environments.

---

### Error: "Import Error" or "Module not found"

**Cause:** Python dependencies not installed or wrong Python environment

**Solution:**

**Check 1:** Verify Poetry environment activated
```powershell
cd apps/api
poetry env info  # Shows active virtualenv
```

**Check 2:** Install dependencies if missing
```powershell
cd apps/api
poetry install  # Install all pyproject.toml dependencies
```

**Check 3:** Use Poetry context for script execution
```powershell
# WRONG - may fail with import errors
python scripts/admin/generate_jwt.py

# CORRECT - Poetry virtualenv with all dependencies
cd apps/api
poetry run python ../../scripts/admin/generate_jwt.py
```

**Alternative:** Standalone dependencies (if Poetry unavailable)
```cmd
pip install -r scripts/requirements.txt
python scripts/admin/generate_jwt.py
```

---

### Path Handling (Windows Compatibility)

**Best Practice:** Use forward slash `/` for cross-platform compatibility

**Why:** Most modern Windows tools (Python, Git, Docker) support forward slash:
```powershell
# Both work on Windows
poetry run python ../../scripts/admin/generate_jwt.py
poetry run python ..\..\scripts\admin\generate_jwt.py
```

**Exceptions requiring backslash:**
- cmd.exe built-in commands (cd, dir, copy)
- Some legacy Windows-only tools

**Recommendation:** Use forward slash `/` in documentation for portability unless Windows-specific context requires backslash.

---

## Further Documentation

**Related Documentation:**
- `ISTRUZIONI-USO-VARIABILI-AMBIENTE.md` - Complete environment variables guide
- `docs/troubleshooting/` - Detailed troubleshooting guides
- `docs/operations/docker-setup-guide.md` - Docker setup and troubleshooting
- `docs/operations/environment-setup.md` - Development environment setup
- `apps/api/README.md` - API-specific documentation
- `.env.example` - Template environment variables with descriptions

**Script Subdirectories:**
- `scripts/admin/README.md` - Admin scripts detailed documentation
- `scripts/ingestion/README.md` - Ingestion scripts detailed documentation
- `scripts/validation/README.md` - Validation scripts detailed documentation

---

## Testing Scripts

**Location:** `scripts/ingestion/test_*.py`, `scripts/validation/test_*.py`

**Usage (Poetry - Recommended):**
```powershell
cd apps/api
poetry run pytest ../../scripts/ingestion/test_ingest_all_documents.py -v
```

**Alternative (pip):**
```cmd
cd scripts
pip install -r requirements.txt
python -m pytest ingestion/test_ingest_all_documents.py -v
```

**Coverage:**
- Unit tests: Function-level validation
- Integration tests: End-to-end workflow validation with running services

---

## Directory Structure

```
scripts/
├── admin/                      # Admin JWT, embeddings management
│   ├── generate_jwt.py
│   ├── generate_missing_embeddings.py
│   └── README.md
├── ingestion/                  # Document ingestion utilities
│   ├── ingest_all_documents.py
│   ├── ingest_single_document.py
│   ├── verify_ingestion.py
│   ├── test_ingest_all_documents.py
│   ├── test_integration_batch_ingestion.py
│   └── README.md
├── perf/                       # Performance testing
│   ├── run_p95_with_warmup.ps1
│   ├── run_p95.ps1
│   ├── warmup_classification_cache.py
│   ├── summarize_p95.py
│   └── p95_local_test.js
├── validation/                 # System validation and integrity
│   ├── validate_rag_system.py
│   ├── database_integrity_audit.py
│   ├── run_chunk_integrity_check.ps1
│   ├── cleanup_test_data.py
│   ├── config_gap_analysis.py
│   ├── database_connectivity_test.py
│   ├── docker_health_check.py
│   ├── env_audit.py
│   ├── generate_test_tokens.py
│   ├── verify_chunk_ids.py
│   └── README.md
├── security/                   # Security scanning (Bash only)
│   └── run_secret_scans.sh
├── ops/                        # Operations utilities
│   ├── watcher-debug.ps1
│   └── watcher-debug.sh
├── README.md                   # This file
└── requirements.txt            # Python dependencies for standalone execution
```

---

## Contributing

When adding new scripts:
1. Document in appropriate section of this README
2. Add required environment variables to table
3. Provide Windows cmd AND PowerShell examples
4. Include expected output examples
5. Add troubleshooting entries for common errors
6. Update `scripts/docs-coverage-8.6.md` coverage audit

**Testing Requirements:**
- Test commands on Windows cmd.exe
- Test commands on PowerShell 5.1+
- Verify path handling (forward/backslash)
- Document platform-specific requirements
- Use per-session ExecutionPolicy Bypass for PowerShell scripts

---

**Version:** 2.0 (Story 8.6 - Windows Refinement)  
**Last Updated:** 2025-11-11  
**Verified On:** Windows 10/11, cmd.exe, PowerShell 5.1+
