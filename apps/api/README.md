# API Service - FisioRAG Backend.

Servizio FastAPI per knowledge base management, RAG retrieval e student authentication.

## Architettura

- **Framework**: FastAPI + Uvicorn
- **Task Queue**: Celery + Redis
- **Database**: Supabase (PostgreSQL + PGVector)
- **LLM**: OpenAI GPT-5-nano (Story 2.12)
- **Dependency Management**: Poetry

## Setup Locale

### Prerequisites

- Python 3.11+
- Poetry
- Supabase account
- Redis (via Docker)

### Installation

```powershell
cd apps/api
poetry install
```

### Environment Variables

Copiare `ENV_TEST_TEMPLATE.txt` (presente in `apps/api/`) nella root del progetto come `.env` e configurare le variabili necessarie:

**Supabase Configuration**:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_KEY` - Service role key (admin operations)
- `SUPABASE_ANON_KEY` - Anonymous key (public operations)
- `SUPABASE_JWT_SECRET` - JWT signing secret

**OpenAI Configuration**:
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_MODEL` - Model name (default: gpt-5-nano)

**Celery Configuration**:
- `CELERY_BROKER_URL` - Redis broker URL (default: redis://localhost:6379/0)
- `CELERY_RESULT_BACKEND` - Redis result backend (default: redis://localhost:6379/0)

**Feature Flags**:
- `CLASSIFICATION_CACHE_ENABLED` - Enable classification cache (Story 2.9)
- `CLASSIFICATION_CACHE_TTL_SECONDS` - Cache TTL in seconds
- `ENABLE_CROSS_ENCODER_RERANKING` - Enable cross-encoder reranking (Story 7.2)
- `ENABLE_DYNAMIC_MATCH_COUNT` - Enable dynamic match count (Story 7.2)
- `ENABLE_CHUNK_DIVERSIFICATION` - Enable chunk diversification (Story 7.2)

Riferimento completo: `../../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`

### Development Server

```powershell
cd apps/api
poetry run uvicorn api.main:app --reload
```

L'API sarà disponibile su http://localhost:8000

## Struttura Directory

```
api/
├── api/                    # Codice sorgente
│   ├── routers/           # Endpoint FastAPI
│   │   ├── chat.py        # Chat endpoints
│   │   ├── admin.py       # Admin endpoints
│   │   └── auth.py        # Authentication endpoints
│   ├── services/          # Business logic
│   │   ├── rag_service.py         # RAG retrieval logic
│   │   ├── classification_service.py  # Classification cache
│   │   └── auth_service.py        # Authentication logic
│   ├── models/            # Pydantic models
│   │   ├── chat.py        # Chat request/response models
│   │   ├── documents.py   # Document models
│   │   └── auth.py        # Auth models
│   ├── knowledge_base/    # Ingestion, chunking, extraction
│   │   ├── ingestion.py   # Document ingestion
│   │   ├── chunking.py    # Chunking strategies
│   │   └── extraction.py  # Text extraction
│   ├── core/              # Config, DI, lifespan
│   │   ├── config.py      # Pydantic Settings configuration
│   │   ├── di.py          # Dependency injection
│   │   └── lifespan.py    # FastAPI lifespan events
│   ├── celery_app.py     # Celery task queue
│   └── main.py           # FastAPI application entry point
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Pytest fixtures
└── pyproject.toml        # Poetry dependencies

```

## Testing

### Unit Tests

```powershell
cd apps/api
poetry run pytest tests/unit/ -v
```

### Integration Tests

```powershell
poetry run pytest tests/integration/ -v
```

### Coverage Report

```powershell
poetry run pytest --cov=api --cov-report=html
```

Report HTML disponibile in `htmlcov/index.html`

### Test Markers

Eseguire test per categoria:

```powershell
# Solo test rapidi
poetry run pytest -m "not slow"

# Solo test che richiedono OpenAI
poetry run pytest -m requires_openai

# Solo test integration
poetry run pytest -m integration
```

## Feature Flags

### Classification Cache (Story 2.9)

Cache per risultati di classificazione chunk per ridurre latenza.

```bash
CLASSIFICATION_CACHE_ENABLED=true
CLASSIFICATION_CACHE_TTL_SECONDS=604800  # 7 giorni
```

**Benefici**:
- Riduzione latenza p95 da 2.1s a 1.5s
- Risparmio chiamate LLM per chunk già classificati

### Advanced Retrieval (Story 7.2)

Feature sperimentali per migliorare qualità retrieval.

```bash
ENABLE_CROSS_ENCODER_RERANKING=false
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false
```

**Nota**: Disabilitati di default, da abilitare per testing.

## Celery Workers

### Start Worker

```powershell
cd apps/api
poetry run celery -A api.celery_app:celery_app worker --loglevel=INFO
```

### Monitor Tasks

**Flower UI** (web-based monitoring):
```powershell
poetry run celery -A api.celery_app:celery_app flower
```

Apri http://localhost:5555 per dashboard Flower.

**Redis CLI**:
```powershell
redis-cli KEYS "celery-*"
```

### Task Queue

Task asincroni gestiti da Celery:
- Ingestion documenti (chunking + embedding generation)
- Batch processing di documenti multipli
- Background maintenance jobs

## API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### OpenAPI Spec

Specifica API dettagliata disponibile in:
- `../../docs/architecture/sezione-5-specifica-api-sintesi.md`

### Endpoint Principali

**Chat**:
- `POST /api/v1/chat/sessions/{session_id}/messages` - Invio messaggio
- `POST /api/v1/chat/messages/{message_id}/feedback` - Feedback su risposta

**Admin**:
- `POST /api/v1/admin/knowledge-base/sync-jobs` - Avvia sync job
- `GET /api/v1/admin/documents` - Lista documenti
- `GET /api/v1/admin/debug/classification-cache-stats` - Statistiche cache

**Authentication**:
- `POST /api/v1/auth/login` - Login studente con token
- `POST /api/v1/auth/refresh` - Refresh JWT token

## Pydantic Settings Configuration

Il progetto usa Pydantic Settings v2 per configuration management (Story 2.12).

**File chiave**: `api/core/config.py`

**Esempio configurazione**:
```python
from api.core.config import get_settings

settings = get_settings()

# Accesso config
supabase_url = settings.supabase.url
model_name = settings.openai.model_name
cache_enabled = settings.classification_cache.enabled
```

**Features**:
- Validazione automatica tipi
- Secrets management
- Environment-specific overrides
- Computed fields per configurazioni derivate

Riferimento completo: `../../docs/pydantic-settings-quick-reference.md`

## Troubleshooting

### Error: "SUPABASE_URL not set"

**Causa**: File `.env` mancante o incompleto

**Soluzione**:
1. Copiare `ENV_TEST_TEMPLATE.txt` in `.env`
2. Compilare tutte le variabili richieste
3. Verificare con `poetry run python -c "from api.core.config import get_settings; print(get_settings())"`

### Error: "Redis connection refused"

**Causa**: Redis non running

**Soluzione**:
```powershell
# Start Redis via Docker
docker compose up redis -d

# Verificare connessione
redis-cli ping
```

### Error: "OpenAI API key invalid"

**Causa**: Chiave OpenAI non valida o mancante

**Soluzione**:
1. Verificare `OPENAI_API_KEY` in `.env`
2. Testare chiave: https://platform.openai.com/api-keys
3. Rigenerare chiave se necessario

### Test falliscono con "Module not found"

**Causa**: Dipendenze non installate

**Soluzione**:
```powershell
# Reinstallare dipendenze
poetry install

# Verificare environment
poetry env info
```

### Celery worker non processa task

**Causa**: Worker non avviato o configurazione errata

**Soluzione**:
1. Verificare Redis running: `redis-cli ping`
2. Verificare `CELERY_BROKER_URL` in `.env`
3. Start worker con log verbose: `poetry run celery -A api.celery_app worker --loglevel=DEBUG`
4. Monitorare Flower: http://localhost:5555

## Riferimenti

### Documentazione Architettura

- **Architecture Index**: `../../docs/architecture/index.md`
- **Tech Stack**: `../../docs/architecture/sezione-3-tech-stack.md`
- **Testing Strategy**: `../../docs/architecture/sezione-11-strategia-di-testing.md`
- **Coding Standards**: `../../docs/architecture/sezione-12-standard-di-codifica.md`

### Quick References

- **Pydantic Settings**: `../../docs/pydantic-settings-quick-reference.md`
- **FastAPI Best Practices**: `../../docs/architecture/addendum-fastapi-best-practices.md`
- **LangChain RAG Patterns**: `../../docs/architecture/addendum-langchain-rag-debug-patterns.md`

### Story References

- **Story 2.9**: Classification Cache (Feature flag)
- **Story 2.12**: GPT-5-nano Integration (Pydantic Settings)
- **Story 7.2**: Advanced Retrieval (Feature flags sperimentali)

## Contributors

Sviluppato da Team FisioRAG
