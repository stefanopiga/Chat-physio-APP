# E2E Tests Setup Guide - Story 2.5

Guida rapida per configurazione ed esecuzione test E2E pipeline.

---

## Quick Setup (5 minuti)

### Step 1: Crea file configurazione

```bash
cd apps/api
cp ENV_TEST_TEMPLATE.txt .env.test.local
```

### Step 2: Compila credenziali

Apri `.env.test.local` e sostituisci `<placeholders>`:

```bash
# Obbligatori
SUPABASE_SERVICE_ROLE_KEY=<your-key>
OPENAI_API_KEY=<your-key>
DATABASE_URL=postgresql://...

# Opzionali (per JWT reale)
SUPABASE_JWT_SECRET=<your-secret>
```

### Step 3: Esegui test

```bash
# Tutti i test E2E
poetry run pytest tests/test_pipeline_e2e.py -v

# Test specifico
poetry run pytest tests/test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline_sync_mode -v
```

---

## File Structure

```
apps/api/
├── .env.test.local          # YOUR test config (gitignored) ← CREATE THIS
├── ENV_TEST_TEMPLATE.txt    # Template con placeholders
├── ENV_TEST_SETUP.md        # Documentazione completa setup
├── tests/
│   ├── conftest.py          # Fixtures comuni + env loading
│   ├── test_pipeline_e2e.py # Integration tests (10 tests)
│   └── README_E2E_TESTS.md  # This file
```

---

## Fixtures Disponibili (conftest.py)

### `test_env_config`
Environment configuration (scope: session)

```python
def test_example(test_env_config):
    assert test_env_config["supabase_url"]
```

### `test_document`
Sample document per testing

```python
def test_example(test_document):
    assert "document_text" in test_document
```

### `test_document_large`
Large document (~500 words) per performance testing

### `admin_token`
Admin JWT token (reale se `SUPABASE_JWT_SECRET` configurato, altrimenti mock)

```python
def test_example(admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
```

### `test_client`
FastAPI TestClient configurato

```python
def test_example(test_client, test_document, admin_token):
    response = test_client.post(
        "/api/v1/admin/knowledge-base/sync-jobs",
        json=test_document,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
```

---

## Environment Variables Priority

`conftest.py` carica env vars in questo ordine:

1. `.env.test.local` ✅ (gitignored, highest priority)
2. `.env.test` (template, committed)
3. `.env` (default development)

**Best Practice:** Usa `.env.test.local` per credenziali reali.

---

## Auto-Skip Logic

Tests con marker `@pytest.mark.integration` vengono auto-skipped se:
- Variabili obbligatorie mancanti (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`)
- Environment non configurato

```bash
# Test output con env non configurato:
SKIPPED [1] conftest.py: Test environment not configured (missing env vars)
```

---

## Test Execution Examples

### Run Tutti i Test E2E

```bash
poetry run pytest tests/test_pipeline_e2e.py -v
```

**Output Atteso:**
```
test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline_sync_mode PASSED
test_pipeline_e2e.py::TestPipelineE2E::test_semantic_search_after_indexing PASSED
test_pipeline_e2e.py::TestDatabaseIntegrity::test_no_null_embeddings_after_completion PASSED
...
==================== 10 passed in 45.23s ====================
```

### Run Test Specifico

```bash
poetry run pytest tests/test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline_sync_mode -v -s
```

Flag `-s` mostra print statements.

### Run con Coverage

```bash
poetry run pytest tests/test_pipeline_e2e.py -v --cov=api --cov-report=term-missing
```

### Run Solo Integration Tests

```bash
poetry run pytest -m integration -v
```

### Skip Integration Tests

```bash
poetry run pytest -m "not integration" -v
```

---

## Troubleshooting

### ❌ Test SKIPPED: "Test environment not configured"

**Causa:** Variabili obbligatorie mancanti.

**Fix:**
```bash
# 1. Verifica .env.test.local esiste
ls .env.test.local

# 2. Verifica variabili configurate
poetry run python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.test.local'); print('✅ OPENAI_API_KEY' if os.getenv('OPENAI_API_KEY') else '❌ MISSING')"

# 3. Ricrea da template
cp ENV_TEST_TEMPLATE.txt .env.test.local
# Edit .env.test.local
```

### ❌ Database Connection Error

**Fix:**
```bash
# Test connection
poetry run python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.test.local'); print(os.getenv('DATABASE_URL'))"

# Verify pgvector extension
# psql "$DATABASE_URL" -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### ❌ OpenAI API Rate Limit

**Fix:**
```bash
# Check quota: https://platform.openai.com/usage
# Reduce test parallelism: pytest -n 1
# Use separate test API key con lower rate limits
```

### ❌ JWT Token Error

**Fix:**
```bash
# Verifica SUPABASE_JWT_SECRET configurato
poetry run python -c "from dotenv import load_dotenv; import os; load_dotenv('.env.test.local'); print('✅' if os.getenv('SUPABASE_JWT_SECRET') else '❌ Missing - using mock token')"

# Se missing, test useranno mock token (ok per alcuni test, richiesto per E2E completi)
```

---

## Test Markers

### `@pytest.mark.integration`
Integration tests che richiedono infrastructure (DB, OpenAI, Supabase)

### `@pytest.mark.e2e`
End-to-end tests che richiedono full stack

### `@pytest.mark.slow`
Tests con execution time > 5s

**Usage:**
```bash
# Run solo integration tests
poetry run pytest -m integration

# Skip slow tests
poetry run pytest -m "not slow"

# Run E2E tests
poetry run pytest -m e2e
```

---

## Development Workflow

### Adding New E2E Test

1. Crea test function in `test_pipeline_e2e.py`:
```python
@pytest.mark.integration
def test_my_feature(test_client, admin_token):
    response = test_client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
```

2. Use fixtures da `conftest.py` (no duplicate)

3. Mark con `@pytest.mark.integration` per auto-skip

4. Run test:
```bash
poetry run pytest tests/test_pipeline_e2e.py::test_my_feature -v
```

### Adding New Fixture

Add to `conftest.py`:
```python
@pytest.fixture
def my_fixture(test_env_config):
    # Setup
    value = create_test_data()
    
    yield value
    
    # Teardown (optional)
    cleanup_test_data()
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test-e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    env:
      SUPABASE_URL: ${{ secrets.TEST_SUPABASE_URL }}
      SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.TEST_SUPABASE_SERVICE_KEY }}
      OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_API_KEY }}
      DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
      CELERY_ENABLED: false
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Poetry
        run: pip install poetry
      
      - name: Install dependencies
        run: poetry install
        working-directory: apps/api
      
      - name: Run E2E tests
        run: poetry run pytest tests/test_pipeline_e2e.py -v
        working-directory: apps/api
```

**Setup:** Add secrets in repository settings → Secrets → Actions.

---

## Manual E2E Validation Checklist

Se test automatici non disponibili, validation manuale:

**Location:** `tests/test_security_validation.py` (lines 222-302)

**Steps:**
1. Upload document via API
2. Verify chunks in database
3. **CRITICAL:** Verify NO NULL embeddings
4. Test semantic search
5. Test chat with citations
6. Verify rate limiter (11th request → 429)
7. Test path security

**Estimated Time:** 2 hours

---

## Security Notes

⚠️ **IMPORTANT:**

1. **NEVER commit `.env.test.local`** - gitignored for security
2. **Use test credentials** - separate from production
3. **Test database only** - DATABASE_URL must be test instance
4. **Rotate keys** - test keys should expire regularly
5. **Limit budget** - set spending limits per test OpenAI key

---

## References

- **Setup Guide:** `apps/api/ENV_TEST_SETUP.md` (detailed documentation)
- **Template:** `apps/api/ENV_TEST_TEMPLATE.txt` (copy to `.env.test.local`)
- **Fixtures:** `apps/api/tests/conftest.py` (configuration + fixtures)
- **Story:** `docs/stories/2.5.intelligent-document-preprocessing.md`
- **Quality Gate:** `docs/qa/gates/2.5-intelligent-document-preprocessing-pipeline-completion.yml`

---

**Setup Time:** ~5 minutes (with existing credentials)  
**Test Execution:** ~45 seconds (10 integration tests)

**Status:** ✅ Ready for execution dopo configurazione .env.test.local

