# Integration Tests

Test di integrazione cross-app per verificare interazioni tra componenti del sistema FisioRAG.

## Struttura

```
tests/
└── integration/          # Test integrazione tra componenti
    ├── test_ingestion_pipeline.py    # Pipeline ingestion E2E
    ├── test_chat_flow.py              # Flusso chat completo
    └── ...
```

## Esecuzione

```powershell
# Run all integration tests
cd tests
pytest integration/ -v

# Run specific test
pytest integration/test_ingestion_pipeline.py -v

# Run with coverage
pytest integration/ --cov=../apps/api/api --cov-report=term-missing
```

## Convenzioni Testing

### Naming

- File test: `test_<feature>.py`
- Test functions: `test_<scenario>_<expected_result>`
- Test classes: `Test<Feature>`

Esempio:
```python
def test_ingestion_pipeline_creates_chunks():
    """Test che pipeline ingestion crea chunks nel database."""
    pass

class TestChatFlow:
    def test_chat_message_returns_response(self):
        """Test che invio messaggio ritorna risposta AI."""
        pass
```

### Fixtures

Usare pytest fixtures per setup/teardown:

```python
import pytest

@pytest.fixture
def test_document():
    """Fixture documento di test."""
    return {
        "file_name": "test.docx",
        "content": "Test content"
    }

@pytest.fixture(scope="module")
def api_client():
    """Client API condiviso per test module."""
    return APIClient(base_url="http://localhost")
```

### Markers

Classificare test con markers:

```python
import pytest

@pytest.mark.integration
def test_api_database_integration():
    """Test integrazione API-database."""
    pass

@pytest.mark.slow
def test_full_ingestion():
    """Test ingestion completo (lento)."""
    pass

@pytest.mark.requires_openai
def test_embedding_generation():
    """Test generazione embedding."""
    pass
```

Eseguire test per marker:
```powershell
pytest -m integration    # Solo test integration
pytest -m "not slow"     # Escludi test lenti
```

### Assertions

Usare assertions esplicite e descrittive:

```python
# ❌ Bad
assert result

# ✅ Good
assert result is not None, "Result should not be None"
assert len(chunks) > 0, f"Expected chunks, got {len(chunks)}"
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
```

### Test Data Cleanup

Sempre cleanup dati di test:

```python
import pytest

@pytest.fixture
def cleanup_test_data():
    """Cleanup dati test dopo esecuzione."""
    yield
    # Cleanup dopo test
    db.delete_test_chunks()
    db.delete_test_documents()
```

### Environment

Test integration richiedono:
- Docker compose up (API + Redis + Celery)
- File `.env` configurato
- Database Supabase attivo

Verificare environment prima di test:
```python
import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def verify_environment():
    """Verifica environment prima di test."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing env vars: {missing}")
```

## Test Specifici per App

I test unitari specifici per app sono organizzati separatamente:

### Backend (apps/api/tests/)

Test unitari e integration per FastAPI backend:

```powershell
cd apps/api
poetry run pytest -v

# Con coverage
poetry run pytest --cov=api --cov-report=html
```

Struttura:
- `unit/` - Test unitari business logic
- `integration/` - Test integrazione database/API
- `conftest.py` - Fixtures condivise

### Frontend (apps/web/tests/)

Test unitari (Vitest) e E2E (Playwright) per React frontend:

```powershell
cd apps/web

# Unit tests (Vitest)
npm test
npm run test:coverage

# E2E tests (Playwright)
npm run test:e2e
```

Struttura:
- `src/**/__tests__/` - Test unitari componenti
- `tests/` - Test E2E Playwright

## Best Practices

### 1. Isolamento Test

Ogni test deve essere indipendente:
- Non dipendere da ordine esecuzione
- Cleanup dati tra test
- Usare fixtures per setup

### 2. Fast Feedback

- Test veloci per CI/CD
- Mock external services quando possibile
- Usare markers per separare test lenti

### 3. Readable Tests

- Test come documentazione
- Nome descrittivo scenario
- Arrange-Act-Assert pattern

```python
def test_chat_returns_relevant_response():
    # Arrange
    session_id = create_test_session()
    question = "Cos'è la radicolopatia lombare?"
    
    # Act
    response = chat_api.send_message(session_id, question)
    
    # Assert
    assert response.status == "success"
    assert "lombare" in response.answer.lower()
    assert len(response.citations) > 0
```

### 4. Error Cases

Testare anche casi errore:

```python
def test_chat_handles_invalid_session():
    """Test gestione sessione invalida."""
    response = chat_api.send_message("invalid-id", "test")
    assert response.status_code == 404
    assert "session not found" in response.error.lower()
```

## CI/CD Integration

Integration test possono essere eseguiti in CI/CD pipeline:

```yaml
# .github/workflows/integration-tests.yml
- name: Start Services
  run: docker compose up -d
  
- name: Wait for Services
  run: |
    timeout 60 bash -c 'until curl -f http://localhost/health; do sleep 2; done'
  
- name: Run Integration Tests
  run: pytest tests/integration/ -v --junit-xml=test-results.xml
  
- name: Cleanup
  run: docker compose down -v
  if: always()
```

## Troubleshooting

### Test falliscono con "Connection refused"

Verificare Docker services running:
```powershell
docker compose ps
curl http://localhost/health
```

### Test lenti su embedding generation

Mockare OpenAI client per test veloci:
```python
from unittest.mock import Mock, patch

@patch('openai.Embedding.create')
def test_embedding_generation(mock_create):
    mock_create.return_value = Mock(data=[Mock(embedding=[0.1]*1536)])
    # Test logic
```

### Database cleanup non funziona

Usare transazioni o fixture con scope:
```python
@pytest.fixture(scope="function", autouse=True)
def reset_database():
    """Reset database tra test."""
    yield
    db.execute("DELETE FROM document_chunks WHERE metadata->>'test' = 'true'")
```

## Riferimenti

- Pytest documentation: https://docs.pytest.org
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Vitest documentation: https://vitest.dev/
- Playwright documentation: https://playwright.dev/
