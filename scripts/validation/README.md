# RAG System Validation Scripts - Story 2.6

Scripts utility per automatizzare validation checks sistema RAG.

## Scripts Disponibili

### 1. `validate_rag_system.py`

Script principale per validation automatizzata infrastructure e configurazioni.

### 2. `cleanup_test_data.py`

Script per cleanup database (DELETE chunks e documents esistenti).

**Scopo**: Eliminare tutti chunks e documenti esistenti prima di test ingestion fresh. Operazione irreversibile (DELETE, non TRUNCATE). Script legge DATABASE_URL da `.env` file root.

**Usage** (PowerShell):

```powershell
# Opzione A: Con Poetry (da apps/api, usa pyproject.toml dependencies)
cd apps/api
poetry run python ../../scripts/validation/cleanup_test_data.py --confirm
poetry run python ../../scripts/validation/cleanup_test_data.py --confirm --verbose

# Opzione B: Python standalone (da project root, richiede pip install -r scripts/requirements.txt)
python scripts/validation/cleanup_test_data.py --confirm
python scripts/validation/cleanup_test_data.py --confirm --verbose

# Opzione C: Dentro container API (Poetry già disponibile)
docker exec fisio-rag-api poetry run python /app/scripts/validation/cleanup_test_data.py --confirm --verbose
```

**Output**:
- Conteggi prima cleanup: N chunks, M documents
- Conteggi dopo cleanup: chunks_deleted, documents_deleted
- Messaggio conferma: "✅ Cleanup completato"

**Requirements**: 
- **Con Poetry**: Dependencies già disponibili in `apps/api/pyproject.toml` (psycopg2-binary, python-dotenv)
- **Senza Poetry**: `pip install -r scripts/requirements.txt` (da host)

---

### 3. `validate_rag_system.py` (dettagli)

Script principale per validation automatizzata infrastructure e configurazioni.

**Checks eseguiti**:
- Environment variables (SUPABASE_URL, OPENAI_API_KEY, etc.)
- Docker services status (api, celery-worker, redis)
- Redis connectivity
- API health endpoint
- OpenAI API key validity

**Usage** (PowerShell Windows):

```powershell
# Opzione A: Con Poetry (recommended, da apps/api)
cd apps/api
poetry run python ../../scripts/validation/validate_rag_system.py
poetry run python ../../scripts/validation/validate_rag_system.py --output ../../reports/validation.json --verbose

# Opzione B: Python standalone (da project root, richiede pip install)
pip install -r scripts/requirements.txt
python scripts/validation/validate_rag_system.py
python scripts/validation/validate_rag_system.py --output reports/validation.json --verbose

# Opzione C: Dentro container API (Poetry già disponibile)
docker exec fisio-rag-api poetry run python /app/scripts/validation/validate_rag_system.py --output /app/reports/validation.json --verbose
```

**Note**: Script legge variabili ambiente da `.env` file root (file esiste e funziona).

**Requirements**:

Script richiede dipendenze in `scripts/requirements.txt`:
- `requests`: HTTP client per API testing
- `redis`: Redis client per connectivity test

```bash
# Install from requirements file
pip install -r scripts/requirements.txt
```

**Output**:

JSON report con struttura:

```json
{
  "validation_run": {
    "timestamp": "2025-10-07T15:30:00Z",
    "script_version": "1.0.0",
    "story": "2.6"
  },
  "summary": {
    "PASS": 5,
    "FAIL": 2,
    "WARN": 1,
    "SKIP": 0
  },
  "overall_status": "FAIL",
  "checks": [
    {
      "check_id": "ENV-001",
      "check_name": "Environment Variables",
      "status": "PASS",
      "details": { "vars_checked": 4 },
      "timestamp": "2025-10-07T15:30:01Z"
    },
    ...
  ]
}
```

**Exit Codes**:
- `0`: PASS (tutti check passed)
- `1`: FAIL (almeno un check failed)
- `2`: WARN (warning presenti, nessun failure)

## Manual Validation

Per validation checks che richiedono interazione manuale (pipeline E2E, semantic search test):

Segui checklist: `docs/qa/manual-e2e-validation-checklist-2.6.md`

## Integration con CI/CD

Script può essere integrato in CI/CD pipeline:

```yaml
# .github/workflows/validation.yml
- name: Validate RAG System
  run: |
    docker compose up -d
    sleep 10  # Wait for services startup
    python scripts/validation/validate_rag_system.py --output validation-results.json
  continue-on-error: true

- name: Upload Validation Report
  uses: actions/upload-artifact@v3
  with:
    name: validation-report
    path: validation-results.json
```

## Development

**Aggiungere nuovo check**:

1. Creare metodo in `RAGSystemValidator`:

```python
def check_my_component(self) -> ValidationResult:
    """AC#: Descrizione check."""
    self.log("Checking my component...")

    try:
        # Logic check
        result = do_validation()

        if result.is_valid:
            self.add_result(
                "COMP-001",
                "My Component",
                "PASS",
                {"details": "ok"}
            )
        else:
            self.add_result(
                "COMP-001",
                "My Component",
                "FAIL",
                {"error": result.error}
            )

    except Exception as e:
        self.add_result(
            "COMP-001",
            "My Component",
            "FAIL",
            {"error": str(e)}
        )
```

2. Aggiungere chiamata in `run_all_checks()`:

```python
def run_all_checks(self):
    # ... existing checks
    self.check_my_component()
```

## Troubleshooting

**Script fails con "Connection refused" (API check)**:
- Verifica Docker services running: `docker compose ps`
- Verifica API accessibile: `curl http://localhost/health`
- Verifica Traefik proxy running: `docker logs fisio-rag-proxy`
- API endpoint via proxy su porta 80, non diretta 8000

**Script fails con "Connection refused" (Redis check)**:
- Se esegui da host: Redis non espone porta di default nel docker-compose.yml
- Aggiungi porta mapping se necessario: `ports: ["6379:6379"]` per servizio `redis`
- O esegui script dentro container: `docker exec fisio-rag-api python ...`

**Script skips database checks**:
- Expected: Supabase database richiede connection string specifica o supabase-py client
- Per ora database checks tramite manual checklist con SQL queries

**OpenAI check fails con "Invalid API key"**:
- Verifica `.env` file presente in project root
- Verifica `OPENAI_API_KEY=sk-...` (formato corretto)
- Test key validità: https://platform.openai.com/api-keys

## Roadmap

**Future enhancements**:
- [ ] Database integrity checks (NULL embeddings via Supabase client)
- [ ] Celery worker health check (task enqueue + result)
- [ ] Pipeline E2E automation (document upload → search → chat)
- [ ] Performance benchmarks (latency targets)
- [ ] Security audit checks (exposed secrets, weak configs)

