# Test Environment Setup - Story 2.5

Guida configurazione environment per esecuzione test E2E.

---

## Quick Start

### Step 1: Crea file di configurazione test

Crea file `.env.test.local` in `apps/api/`:

```bash
cd apps/api
cp ENV_TEST_TEMPLATE.txt .env.test.local
```

### Step 2: Compila valori reali

Apri `.env.test.local` e sostituisci placeholder:

```bash
# Supabase Configuration
SUPABASE_URL=https://**************************.supabase.co
SUPABASE_ANON_KEY=<your-actual-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-actual-service-role-key>
SUPABASE_JWT_SECRET=<your-actual-jwt-secret>
SUPABASE_PROJECT_ID="<your-project-id>"
SUPABASE_JWT_ISSUER=https://*********************.supabase.co/auth/v1

# Database Configuration (use test database!)
DATABASE_URL=postgresql://postgres.**************:<password>@aws-1-eu-central-2.pooler.supabase.com:6543/postgres

# OpenAI Configuration
OPENAI_API_KEY=<your-openai-api-key>
LLM_API_KEY=<your-llm-api-key>
EMBEDDING_API_KEY=<your-embedding-api-key>

# Celery Configuration (set false for test isolation)
CELERY_ENABLED=false
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT Configuration
SUPABASE_JWT_AUDIENCE=authenticated
TEMP_JWT_EXPIRES_MINUTES=15

# Rate Limiting Configuration
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC=60
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS=10

# Admin Configuration
ADMIN_EMAIL=<value>

# Analytics Configuration
AG_LATENCY_MAX_SAMPLES=200
```

### Step 3: Esegui test E2E

```bash
# Test E2E completi
poetry run pytest tests/test_pipeline_e2e.py -v

# Test specifico
poetry run pytest tests/test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline_sync_mode -v

# Con coverage
poetry run pytest tests/test_pipeline_e2e.py -v --cov=api --cov-report=term-missing
```

---

## Environment Variables Reference

### Variabili Obbligatorie (E2E Tests)

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key (admin) | `eyJhbGciOi...` |
| `OPENAI_API_KEY` | OpenAI API key per embeddings | `sk-proj-...` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |

⚠️ **CRITICAL:** Usa test database separato, NON production!

### Variabili Opzionali

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_ANON_KEY` | Anon key per client-side | Required for full stack |
| `SUPABASE_JWT_SECRET` | JWT secret per token generation | Mock token if missing |
| `CELERY_ENABLED` | Enable Celery async processing | `false` (sync for tests) |
| `ADMIN_EMAIL` | Admin email per JWT payload | `test@example.com` |

---

## Test Database Setup

### Option 1: Supabase Test Project (Recommended)

1. Crea nuovo progetto Supabase per testing
2. Run migrations:
   ```bash
   supabase db push --db-url "postgresql://..."
   ```
3. Configura `DATABASE_URL` con test project URL

### Option 2: Local PostgreSQL

1. Setup local PostgreSQL con pgvector:
   ```bash
   docker run -d \
     --name postgres-test \
     -e POSTGRES_PASSWORD=test \
     -e POSTGRES_DB=fisiorag_test \
     -p 5433:5432 \
     ankane/pgvector
   ```

2. Run migrations:
   ```bash
   psql -h localhost -p 5433 -U postgres -d fisiorag_test -f supabase/migrations/*.sql
   ```

3. Configura `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql://postgres:test@localhost:5433/fisiorag_test
   ```

---

## File Configuration Priority

`conftest.py` carica environment variables in questo ordine:

1. `.env.test.local` (gitignored, highest priority)
2. `.env.test` (template, committed)
3. `.env` (default development)

**Best Practice:** Usa `.env.test.local` per valori reali (gitignored).

---

## Template File Reference

### File: `ENV_TEST_TEMPLATE.txt`

Template con placeholder per quick setup:

```bash
# Supabase Configuration
SUPABASE_URL=https://****************.supabase.co
SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>
SUPABASE_PROJECT_ID="<your-project-id>"
SUPABASE_JWT_ISSUER=https://**********************.supabase.co/auth/v1

# Database Configuration
DATABASE_URL=postgresql://postgres.*************:<password>@aws-1-eu-central-2.pooler.supabase.com:6543/postgres

# OpenAI Configuration
OPENAI_API_KEY=<your-openai-api-key>
LLM_API_KEY=<your-llm-api-key>
EMBEDDING_API_KEY=<your-embedding-api-key>

# Celery Configuration
CELERY_ENABLED=false
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# JWT Configuration
SUPABASE_JWT_AUDIENCE=authenticated
TEMP_JWT_EXPIRES_MINUTES=15

# Rate Limiting Configuration
EXCHANGE_CODE_RATE_LIMIT_WINDOW_SEC=60
EXCHANGE_CODE_RATE_LIMIT_MAX_REQUESTS=10

# Admin Configuration
ADMIN_EMAIL=<value>

# Analytics Configuration
AG_LATENCY_MAX_SAMPLES=200
```

**Copy Command:**
```bash
cp ENV_TEST_TEMPLATE.txt .env.test.local
# Edit .env.test.local and replace <placeholders>
```

---

## Troubleshooting

### Test SKIPPED: "Test environment not configured"

**Causa:** Variabili obbligatorie mancanti.

**Soluzione:**
1. Verifica `.env.test.local` esiste
2. Check variabili: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `DATABASE_URL`
3. Ricarica environment: `poetry run pytest --cache-clear`

### Database Connection Error

**Causa:** `DATABASE_URL` non valido o database non accessibile.

**Soluzione:**
1. Test connection: `psql "$DATABASE_URL" -c "SELECT version()"`
2. Verifica migrations: `supabase db push`
3. Check firewall/network access

### OpenAI API Error

**Causa:** `OPENAI_API_KEY` invalido o rate limit.

**Soluzione:**
1. Verifica key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
2. Check quota: https://platform.openai.com/usage
3. Use test key con rate limits bassi

### JWT Token Error

**Causa:** `SUPABASE_JWT_SECRET` mancante o invalido.

**Soluzione:**
1. Se secret disponibile, aggiungi a `.env.test.local`
2. Altrimenti, test useranno mock token (unit tests only)
3. Per E2E tests, JWT secret è required

---

## Security Notes

⚠️ **IMPORTANT:**

1. **NEVER commit `.env.test.local`** - è gitignored per motivo
2. **Use test credentials only** - mai production keys
3. **Separate test database** - `DATABASE_URL` must be test instance
4. **Rotate keys regularly** - test keys should expire
5. **Limit OpenAI budget** - set spending limits per test key

---

## CI/CD Integration

Per GitHub Actions o CI pipeline:

```yaml
# .github/workflows/test-e2e.yml
env:
  SUPABASE_URL: ${{ secrets.TEST_SUPABASE_URL }}
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.TEST_SUPABASE_SERVICE_KEY }}
  OPENAI_API_KEY: ${{ secrets.TEST_OPENAI_API_KEY }}
  DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
  CELERY_ENABLED: false

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run E2E tests
        run: poetry run pytest tests/test_pipeline_e2e.py -v
```

**Setup:** Add secrets in repository settings → Secrets → Actions.

---

## Test Execution Checklist

Pre-execution checklist:

- [ ] `.env.test.local` created and configured
- [ ] Test database setup completed (migrations run)
- [ ] OpenAI API key valid and has quota
- [ ] Supabase project accessible
- [ ] Dependencies installed: `poetry install`
- [ ] Database truncated (fresh state): `poetry run pytest --cache-clear`

Execution:

```bash
# Step 1: Verify configuration
poetry run python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.test.local'); print('✅' if os.getenv('OPENAI_API_KEY') else '❌')"

# Step 2: Run tests
poetry run pytest tests/test_pipeline_e2e.py -v

# Step 3: Check results
# All tests should PASS (not SKIPPED)
```

---

## References

- Story: `docs/stories/2.5.intelligent-document-preprocessing.md`
- Quality Gate: `docs/qa/gates/2.5-intelligent-document-preprocessing-pipeline-completion.yml`
- Manual E2E Checklist: `tests/test_security_validation.py` (lines 222-302)
- Test Configuration: `tests/conftest.py`

---

**Setup Time:** ~15 minutes (with existing Supabase project)  
**Test Execution Time:** ~2-5 minutes (10 integration tests)

**Status:** Ready for execution after configuration

