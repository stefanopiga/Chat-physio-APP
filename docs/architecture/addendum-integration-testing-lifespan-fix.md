# Addendum: Integration Testing Lifespan Fix (Story 2.4.1)

**Status**: Active  
**Priority**: Critical - Blocking Test Execution  
**Date**: 2025-10-05  
**Target**: Backend Engineers

---

## 1. Problema

I test di integrazione per l'endpoint `/api/v1/admin/knowledge-base/sync-jobs` (Story 2.4.1) falliscono con:

```
RuntimeError: Database pool non inizializzato
```

### Causa Radice

`TestClient(app)` esegue il lifespan manager di FastAPI che chiama `init_db_pool()`. Questa funzione richiede `DATABASE_URL` e tenta connessione reale al database PostgreSQL.

**Pattern errato:**
```python
@pytest.fixture
def client():
    return TestClient(app)  # ❌ Esegue lifespan → init_db_pool → richiede DATABASE_URL

def test_endpoint(client, mock_db_conn):
    response = client.post("/api/v1/admin/knowledge-base/sync-jobs", ...)
```

---

## 2. Soluzione Implementata

### Pattern 1: Mock Lifespan Functions (Isolamento Completo)

Per test di integrazione che NON richiedono database reale:

```python
# apps/api/tests/test_sync_job_integration.py

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from api.main import app, _auth_bridge
from api.database import get_db_connection

@pytest.fixture
def client():
    """
    Test client con database pool mockato.
    
    Mock lifespan functions per evitare connessione reale:
    - init_db_pool: no connessione PostgreSQL
    - close_db_pool: no cleanup reale
    - Dependency injection: usa mock_db_conn fixture
    """
    with patch("api.database.init_db_pool", new_callable=AsyncMock):
        with patch("api.database.close_db_pool", new_callable=AsyncMock):
            yield TestClient(app)

@pytest.fixture
def mock_db_conn():
    """Mock asyncpg.Connection per test isolati."""
    async def _get_mock_conn():
        conn = AsyncMock()
        conn.fetchval = AsyncMock(return_value=uuid.uuid4())
        conn.execute = AsyncMock()
        yield conn
    
    app.dependency_overrides[get_db_connection] = _get_mock_conn
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token_override():
    """Override auth dependency."""
    def _override():
        return {"sub": "test_admin", "role": "admin", "app_metadata": {"role": "admin"}}
    
    app.dependency_overrides[_auth_bridge] = _override
    yield
    app.dependency_overrides.clear()
```

**Test Implementation (Sincrono):**

```python
def test_sync_job_full_pipeline(client, admin_token_override, mock_db_conn):
    """Test: Pipeline completa documento → chunk → indexing."""
    with patch("api.ingestion.db_storage.save_document_to_db") as mock_save:
        with patch("api.ingestion.db_storage.update_document_status"):
            with patch("api.knowledge_base.indexer.index_chunks") as mock_index:
                # Arrange
                doc_id = uuid.uuid4()
                mock_save.return_value = doc_id
                mock_index.return_value = 3
                
                # Act
                response = client.post(
                    "/api/v1/admin/knowledge-base/sync-jobs",
                    json={
                        "document_text": "Test content",
                        "metadata": {"document_name": "test.pdf"}
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                # Assert
                assert response.status_code == 200
                assert response.json()["inserted"] == 3
```

---

### Pattern 2: Environment Variable (Database Reale Opzionale)

Per test che richiedono database reale (E2E):

```python
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_database_url():
    """Setta DATABASE_URL per test con database reale."""
    os.environ["DATABASE_URL"] = "postgresql://test_user:test_pass@localhost:5432/test_db"
    yield
    os.environ.pop("DATABASE_URL", None)

@pytest.fixture
def client():
    """TestClient con lifespan completo (connessione reale)."""
    return TestClient(app)
```

---

## 3. Differenze tra Pattern

| Aspetto | TestClient + Mock Lifespan | AsyncClient + ASGITransport |
|---------|---------------------------|----------------------------|
| **Lifespan** | Eseguito con mock | Eseguito realmente |
| **Async/Sync** | Sincrono (conveniente) | Async (più verboso) |
| **Setup** | Semplice | Richiede pytest-asyncio |
| **Performance** | Veloce (no connessione) | Più lento (setup pool) |
| **Isolation** | Completo | Dipende da mock dependencies |
| **Pattern Ufficiale** | Documentato | Documentato (pytest-anyio) |

---

## 4. Best Practices

### 4.1 Quando Usare TestClient (Raccomandato)

- Test di integrazione con mock completi
- Test unitari per endpoint
- Nessun database reale richiesto
- Performance critica (CI/CD)

**Pro:**
- ✅ Sincrono (no async test functions)
- ✅ Setup semplice
- ✅ Veloce
- ✅ Isolation completo

**Contro:**
- ❌ Richiede mock di `init_db_pool` / `close_db_pool`

### 4.2 Quando Usare AsyncClient

- Test E2E con database reale
- Test che verificano comportamento async specifico
- Test che richiedono lifespan reale

**Pro:**
- ✅ Lifespan reale eseguito
- ✅ Simulazione più realistica

**Contro:**
- ❌ Più verboso (async/await ovunque)
- ❌ Richiede pytest-asyncio correttamente configurato
- ❌ Setup più complesso

---

## 5. Common Pitfalls

### ❌ Errore 1: Async Fixture con Sync Test

```python
@pytest.fixture
async def async_client():  # ❌ Async fixture
    async with AsyncClient(...) as client:
        yield client

def test_endpoint(async_client):  # ❌ Sync test con async fixture
    response = async_client.post(...)  # ❌ AttributeError
```

**Soluzione:** Entrambi async o entrambi sync:

```python
# Soluzione 1: Sync
@pytest.fixture
def client():
    return TestClient(app)

def test_endpoint(client):
    response = client.post(...)

# Soluzione 2: Async (pytest-asyncio)
@pytest.fixture
async def async_client():
    async with AsyncClient(...) as client:
        yield client

@pytest.mark.asyncio
async def test_endpoint(async_client):
    response = await async_client.post(...)
```

### ❌ Errore 2: Mock Lifespan Fuori Scope

```python
@pytest.fixture
def client():
    with patch("api.database.init_db_pool"):
        return TestClient(app)  # ❌ Context manager esce prima dell'uso
```

**Soluzione:** Yield dentro context manager:

```python
@pytest.fixture
def client():
    with patch("api.database.init_db_pool"):
        with patch("api.database.close_db_pool"):
            yield TestClient(app)  # ✅ Client vive dentro mock scope
```

### ❌ Errore 3: DATABASE_URL Non Mockato

```python
def test_endpoint():
    client = TestClient(app)  # ❌ Lifespan richiede DATABASE_URL
```

**Soluzione:** Mock lifespan o setta DATABASE_URL:

```python
def test_endpoint():
    with patch("api.database.init_db_pool"):
        client = TestClient(app)  # ✅ Mock previene connessione reale
```

---

## 6. Esecuzione Tests

### Comando Standard

```bash
cd apps/api
poetry run pytest tests/test_sync_job_integration.py -v
```

### Con Coverage

```bash
poetry run pytest tests/test_sync_job_integration.py \
  --cov=api.ingestion \
  --cov-report=term-missing
```

### Singolo Test

```bash
poetry run pytest tests/test_sync_job_integration.py::test_sync_job_full_pipeline -v
```

### Debug Mode

```bash
poetry run pytest tests/test_sync_job_integration.py -vv -s --tb=short
```

---

## 7. Checklist di Verifica

Prima di chiudere task di testing:

- [ ] Test passano con `poetry run pytest` (non `python -m pytest`)
- [ ] Tutti i lifespan dependencies mockati (init_db_pool, close_db_pool)
- [ ] Dependency overrides puliti in teardown (`app.dependency_overrides.clear()`)
- [ ] Test sincroni usano `TestClient` (non `AsyncClient`)
- [ ] Test async marcati con `@pytest.mark.asyncio`
- [ ] Mock services esterni (LLM, embedding, database)
- [ ] No DATABASE_URL reale richiesta in CI/CD
- [ ] Coverage ≥95% per codice critico

---

## 8. Riferimenti

- **Story 2.4.1**: `docs/stories/2.4.1-document-persistence-integrity-fix.md`
- **Test Strategy**: `docs/architecture/sezione-11-strategia-di-testing.md`
- **FastAPI Testing**: https://fastapi.tiangolo.com/advanced/testing-events/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **Existing Tests**: `apps/api/tests/test_document_explorer.py` (pattern reference)

---

## 9. Note Implementative

### Perché TestClient Non Esegue Lifespan di Default

FastAPI >= 0.100.0: `TestClient` esegue automaticamente lifespan events. **Non** serve `LifespanManager` esplicito come in versioni precedenti.

### Gestione Async in TestClient

`TestClient` converte automaticamente async endpoints in sync calls usando `anyio` internamente. Non serve marcare test come async se si usa `TestClient`.

### Cleanup Automatico

`TestClient` gestisce automaticamente:
- Avvio lifespan events (startup)
- Shutdown events (allo scope fixture)
- Context manager cleanup

---

**Status del Fix**: ✅ **COMPLETATO E VERIFICATO** (2025-10-05)

1. ✅ File `test_sync_job_integration.py` aggiornato con pattern corretto
2. ✅ Mock `init_db_pool` / `close_db_pool` implementato
3. ✅ Test convertiti da async a sync (conformi a `TestClient`)
4. ✅ Dependency overrides correttamente gestiti
5. ✅ Pattern conforme a `docs/architecture/sezione-11-strategia-di-testing.md`
6. ✅ **DATABASE_URL** fake settata via fixture session-scoped
7. ✅ **Mock path corretto:** `api.main.index_chunks` (non `api.knowledge_base.indexer.index_chunks`)
8. ✅ **Tutti e 4 test PASSED** (7.13s execution time)

**Risultati Finali:**
```
test_sync_job_full_pipeline ........................... PASSED [25%]
test_sync_job_response_includes_document_id ............ PASSED [50%]
test_sync_job_error_updates_status ..................... PASSED [75%]
test_concurrent_sync_jobs_same_hash .................... PASSED [100%]

4 passed, 1 warning in 7.13s
Coverage: 65% (target 55% per integration tests)
```

**Next Steps:**
1. ✅ Test suite completamente funzionante
2. ⏭️ Committare modifiche al repository
3. ⏭️ Aggiornare Story 2.4.1 status → "Testing Complete"
4. ⏭️ Procedere con gate review finale
