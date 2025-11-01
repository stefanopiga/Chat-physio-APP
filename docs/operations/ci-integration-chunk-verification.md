# Integrazione CI - Verifica Integrità Chunk

**Storia:** 2.11 - Chat RAG End-to-End  
**Requirement:** AC4 - Integrità dei Chunk Verificata  
**Data:** 2025-10-17

## Obiettivo

Garantire che ogni chunk nel database possieda un identificatore univoco e che non esistano duplicati o collisioni, attraverso verifiche automatizzate eseguibili in CI/CD.

## Script Disponibili

### 1. Script Python Standalone

**Path:** `scripts/validation/verify_chunk_ids.py`

```bash
# Esecuzione locale
export DATABASE_URL="postgresql://..."
python scripts/validation/verify_chunk_ids.py
```

**Output:**
- ✅ `document_chunks.id` valori univoci globalmente
- ✅ `(document_id, chunk_index)` coppie univoche
- ❌ Errori se rileva duplicati

### 2. Test Pytest di Integrità

**Path:** `apps/api/tests/test_chunk_integrity.py`

```bash
# Esecuzione con pytest
cd apps/api
poetry run pytest tests/test_chunk_integrity.py -v
```

**Test inclusi:**
- `test_chunk_ids_are_unique` - Verifica ID chunk univoci
- `test_chunk_indexes_per_document_are_unique` - Verifica indici per documento
- `test_chunk_metadata_has_required_fields` - Verifica metadati essenziali
- `test_no_orphaned_chunks` - Verifica assenza chunk orfani

### 3. Script Wrapper Bash

**Path:** `scripts/validation/run_chunk_integrity_check.sh`

Esegue entrambe le verifiche (script Python + pytest) in sequenza.

```bash
chmod +x scripts/validation/run_chunk_integrity_check.sh
export DATABASE_URL="postgresql://..."
./scripts/validation/run_chunk_integrity_check.sh
```

## Integrazione in CI/CD

### Prerequisiti

- `DATABASE_URL` environment variable configurata
- Database popolato con chunk di test o staging
- Poetry installato (per test pytest)

### GitHub Actions (Esempio)

```yaml
name: Chunk Integrity Verification

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  verify-chunks:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: fisio_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Poetry
        run: pip install poetry
      
      - name: Install Dependencies
        working-directory: apps/api
        run: poetry install
      
      - name: Setup Test Database
        run: |
          # Esegui migrazioni e seed dati di test
          psql $DATABASE_URL -f supabase/migrations/*.sql
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/fisio_test
      
      - name: Run Chunk Integrity Tests
        working-directory: apps/api
        run: poetry run pytest tests/test_chunk_integrity.py -v
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/fisio_test
      
      - name: Run Standalone Verification Script
        run: python scripts/validation/verify_chunk_ids.py
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost:5432/fisio_test
```

### GitLab CI (Esempio)

```yaml
verify-chunks:
  stage: test
  image: python:3.11
  services:
    - postgres:15
  variables:
    POSTGRES_DB: fisio_test
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: testpass
    DATABASE_URL: "postgresql://postgres:testpass@postgres:5432/fisio_test"
  before_script:
    - pip install poetry
    - cd apps/api && poetry install
  script:
    - poetry run pytest tests/test_chunk_integrity.py -v
    - cd ../.. && python scripts/validation/verify_chunk_ids.py
```

## Gate di Qualità

I test di integrità chunk sono **obbligatori** per:
- ✅ Merge di PR che modificano ingestion/chunking
- ✅ Deploy su staging/production
- ✅ After ingestion di nuovi documenti

## Cosa Verificare Manualmente

Oltre ai test automatici, verificare periodicamente:

1. **Vincoli Database Attivi**
   ```sql
   SELECT constraint_name, constraint_type 
   FROM information_schema.table_constraints 
   WHERE table_name = 'document_chunks';
   ```

2. **Statistiche Chunk**
   ```sql
   SELECT 
     COUNT(DISTINCT id) as unique_ids,
     COUNT(*) as total_chunks,
     COUNT(DISTINCT document_id) as unique_documents
   FROM document_chunks;
   ```

3. **Chunk Senza Embeddings**
   ```sql
   SELECT COUNT(*) 
   FROM document_chunks 
   WHERE embedding IS NULL;
   ```

## Troubleshooting

### Errore: DATABASE_URL non configurata

```bash
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
```

### Errore: asyncpg non installato

```bash
cd apps/api
poetry add --dev asyncpg
```

### Errore: Chunk duplicati trovati

1. Identificare i duplicati:
   ```sql
   SELECT id, COUNT(*) 
   FROM document_chunks 
   GROUP BY id 
   HAVING COUNT(*) > 1;
   ```

2. Eliminare i duplicati manualmente o re-ingerire i documenti:
   ```bash
   # Backup prima di eliminare!
   DELETE FROM document_chunks WHERE ctid NOT IN (
     SELECT MIN(ctid) FROM document_chunks GROUP BY id
   );
   ```

## Riferimenti

- Story: `docs/stories/2.11.chat-rag-activation.md`
- Gate QA: `docs/qa/gates/2.11-chat-rag-activation.yml`
- Script: `scripts/validation/verify_chunk_ids.py`
- Test: `apps/api/tests/test_chunk_integrity.py`

