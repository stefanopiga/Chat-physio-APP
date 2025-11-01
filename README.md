# FisioRAG

Sistema RAG (Retrieval-Augmented Generation) per assistenza studenti di fisioterapia basato su documentazione scientifica e linee guida cliniche.

## Architettura

Deployment containerizzato orchestrato da **Docker Compose** con 5 servizi:

### Servizi Docker

1. **Traefik (Reverse Proxy)**
   - Gestisce routing HTTP e load balancing
   - Dashboard di monitoraggio su porta configurabile (default: 18080)
   - Router health check dedicato (priority 150) per endpoint `/health`

2. **API (FastAPI)**
   - Backend REST API con FastAPI
   - Health check automatico ogni 30s
   - Montato su `/api` via Traefik

3. **Celery Worker**
   - Worker asincrono per task background
   - Condivide model cache con API
   - Dipende da Redis per job queue

4. **Redis (Alpine)**
   - Message broker per Celery
   - Persistenza AOF abilitata (`redis-server --appendonly yes`)
   - Volume `redis_data` previene perdita dati al restart

5. **Web (Nginx)**
   - Frontend React + TypeScript + Vite + Shadcn/UI
   - Servito tramite Nginx production build
   - Catch-all router Traefik (priority 1)

### Networking

- **physio-rag-net** (bridge network): connette tutti i container
- Comunicazione inter-service tramite nomi DNS automatici

### Volumi Persistenti

- **redis_data**: Persistenza dati Redis (AOF mode)
- **model_cache**: Cache modelli sentence-transformers (~200MB, Story 7.2)
  - Previene re-download del cross-encoder model ad ogni restart
  - Condiviso tra API e Celery Worker

### Database

- **Supabase (PostgreSQL + PGVector)**: Database remoto per embeddings e dati applicativi
- Configurato via variabili d'ambiente (SUPABASE_URL, SUPABASE_SERVICE_KEY)

## Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 18+
- Docker Desktop
- Account Supabase (o istanza locale)

### Setup Ambiente

1. **Clonare il repository**
```bash
git clone <repository-url>
cd APPLICAZIONE
```

2. **Configurare variabili d'ambiente**

Copiare `.env.example` e configurare le credenziali:

```powershell
# PowerShell
Copy-Item .env.example .env
```

```bash
# Bash
cp .env.example .env
```

Modificare `.env` con:
- Credenziali Supabase (URL, Service Key, JWT Secret)
- OpenAI API Key
- Feature flags opzionali (vedi sezione sotto)

**Consultare [ISTRUZIONI-USO-VARIABILI-AMBIENTE.md](ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) per la guida completa.**

3. **Avviare i servizi**

```bash
docker compose up --build -d
```

4. **Verificare disponibilità**

```bash
# Health check API
curl http://localhost/health

# Frontend
curl http://localhost

# Dashboard Traefik (monitoring)
# Default: http://localhost:18080
# Configurabile via TRAEFIK_DASHBOARD_PORT in .env
```

### Primo Avvio

Il sistema sarà disponibile su:
- **Frontend**: http://localhost
- **API**: http://localhost/api
- **Health Check**: http://localhost/health
- **Traefik Dashboard**: http://localhost:18080 (o porta da `TRAEFIK_DASHBOARD_PORT`)

## Feature Flags (Story 7.2)

Le seguenti feature flags avanzate sono configurabili in `.env`:

### 1. Cross-Encoder Reranking
```bash
ENABLE_CROSS_ENCODER_RERANKING=false  # default
```
Abilita reranking di precisione dei risultati con modello Cross-Encoder (~200MB).
- **Pro**: Migliora pertinenza risultati
- **Contro**: Aumenta latenza (~500ms) e download iniziale model cache

### 2. Dynamic Match Count
```bash
ENABLE_DYNAMIC_MATCH_COUNT=false  # default
```
Adatta dinamicamente il numero di chunk recuperati in base alla complessità della domanda.
- Domande semplici: 5 chunk
- Domande complesse: 12 chunk
- Default: 8 chunk

### 3. Chunk Diversification
```bash
ENABLE_CHUNK_DIVERSIFICATION=false  # default
```
Limita chunk per documento sorgente per promuovere diversità delle fonti.
- Max 2 chunk per documento (configurabile)
- Preserva sempre i top 3 risultati

**Nota**: Abilitare tutte le flag migliora la qualità ma aumenta latenza e consumo risorse.

## Comandi Comuni

### Sviluppo

```bash
# Avvio ambiente development (con hot-reload)
docker compose -f docker-compose.dev.yml up

# Stop servizi
docker compose down

# Rebuild dopo modifiche Dockerfile
docker compose up --build

# View logs real-time
docker compose logs -f

# Logs di un servizio specifico
docker compose logs -f api
```

### Testing

```bash
# Backend tests
cd apps/api
poetry install
poetry run pytest

# Frontend tests (unit)
cd apps/web
npm install
npm test

# Frontend tests (E2E)
npm run test:e2e
```

### Produzione

```bash
# Deploy produzione
docker compose up --build -d

# Verifica stato servizi
docker compose ps

# Stop e cleanup completo (include volumi)
docker compose down -v
```

## Struttura Progetto

```
APPLICAZIONE/
├── apps/
│   ├── api/                    # Backend FastAPI
│   │   ├── api/                # Codice sorgente
│   │   ├── tests/              # Test unitari e integration
│   │   ├── Dockerfile          # Multi-stage build Python 3.11
│   │   └── pyproject.toml      # Poetry dependencies
│   └── web/                    # Frontend React
│       ├── src/                # Codice sorgente TypeScript
│       ├── tests/              # Test Vitest + Playwright
│       ├── Dockerfile          # Multi-stage build Node 20 + Nginx
│       └── package.json        # PNPM dependencies
├── conoscenza/                 # Knowledge base documenti (escluso da git)
├── docs/                       # Documentazione tecnica completa
│   ├── architecture/           # Design e architettura
│   ├── api/                    # Specifiche API OpenAPI
│   ├── prd.md                  # Product Requirements Document
│   └── front-end-spec.md       # Specifiche UI/UX
├── scripts/                    # Script operazionali
│   ├── ingestion/              # Pipeline ingestion documenti
│   └── validation/             # Health check e validation
├── supabase/                   # Database migrations e schema
├── tests/                      # Integration tests cross-app
├── .env.example                # Template variabili d'ambiente
├── docker-compose.yml          # Orchestrazione servizi production
├── docker-compose.dev.yml      # Orchestrazione servizi development
└── ISTRUZIONI-USO-VARIABILI-AMBIENTE.md  # Guida configurazione .env
```

### Note sulla Struttura

- **conoscenza/**: Knowledge base locale, esclusa da `.gitignore` (contenuti non versionati)
- **docs/**: Documentazione versionata - consultare per dettagli architettura, API, testing
- **model_cache**: Volume Docker gestito automaticamente (non in filesystem)

## Documentazione

La documentazione completa è disponibile nella cartella `docs/`:
- **Architecture & Design**: `docs/architecture/`
- **API Specifications**: `docs/architecture/sezione-5-specifica-api-sintesi.md`
- **Testing Strategy**: `docs/architecture/sezione-11-strategia-di-testing.md`
- **Deployment Guide**: `docs/architecture/sezione-9-architettura-di-deployment.md`
- **Unified Project Structure**: `docs/architecture/sezione-7-struttura-unificata-del-progetto.md`

## Variabili d'Ambiente Richieste

Variabili essenziali da configurare in `.env`:

```bash
# Supabase
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_KEY=<your-service-key>
SUPABASE_JWT_SECRET=<your-jwt-secret>

# OpenAI
OPENAI_API_KEY=<your-openai-key>

# Redis (configurato automaticamente da Docker)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Traefik (opzionale)
TRAEFIK_DASHBOARD_PORT=18080  # default

# Feature Flags Story 7.2 (opzionali)
ENABLE_CROSS_ENCODER_RERANKING=false
ENABLE_DYNAMIC_MATCH_COUNT=false
ENABLE_CHUNK_DIVERSIFICATION=false
```

**Consultare [ISTRUZIONI-USO-VARIABILI-AMBIENTE.md](ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) per guida dettagliata su ogni variabile.**

**Nota**: Il file `.env.example` contiene 60+ variabili con valori di default e documentazione inline.

## Troubleshooting

### Porta 80 occupata (Windows)

La porta 80 è spesso riservata da Windows per IIS o altri servizi.

```powershell
# Identificare processo su porta 80
netstat -ano | findstr :80

# Terminare processo (come amministratore)
taskkill /PID <process-id> /F

# Oppure modificare porta in docker-compose.yml
# ports:
#   - "8080:80"  # Usa porta 8080 invece
```

### Dashboard Traefik non accessibile

La dashboard Traefik è su porta configurabile (default: 18080).

**Problema**: Porta 18080 occupata su Windows (riservata da sistema).

**Soluzione**: Configurare porta alternativa in `.env`:

```bash
TRAEFIK_DASHBOARD_PORT=19080  # o altra porta libera
```

Verificare:
```bash
curl http://localhost:19080  # o porta configurata
```

### Errore "OpenAI API Error"

**Cause comuni:**
- API Key non valida o scaduta
- Credito OpenAI esaurito
- Rate limiting (troppi request)

**Verifica:**
```bash
# Controllare validità chiave
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer <your-openai-key>"
```

**Soluzione**: Verificare credito su https://platform.openai.com/account/usage

### Container fails to start

**Causa**: Configurazione `.env` errata o credenziali Supabase invalide.

**Verifica logs:**
```bash
docker compose logs api
docker compose logs celery-worker
```

**Test connessione Supabase:**
```bash
cd scripts/validation
poetry run python database_connectivity_test.py
```

### Reset completo ambiente

Rimuove container, volumi e network:

```bash
# Stop e rimozione completa
docker compose down -v

# Rebuild da zero
docker compose up --build

# Verifica pulizia volumi
docker volume ls | grep physio-rag
```

**Attenzione**: L'opzione `-v` rimuove anche `redis_data` (perdita dati Redis) e `model_cache` (re-download ~200MB).

### Model cache non funzionante

**Sintomo**: Cross-encoder model (~200MB) si scarica ad ogni restart.

**Verifica volume:**
```bash
docker volume inspect applicazione_model_cache
```

**Soluzione**: Verificare mount point in `docker-compose.yml`:
```yaml
volumes:
  - model_cache:/app/.cache/torch/sentence_transformers
```

### Health check fallito

**Sintomo**: `curl http://localhost/health` ritorna errore.

**Verifica stato servizi:**
```bash
docker compose ps
# Verificare che api sia "healthy"

# Test health check interno
docker exec physio-rag-api curl http://localhost:8000/health
```

**Soluzione**: Verificare routing Traefik su dashboard:
- http://localhost:18080 (o porta da `TRAEFIK_DASHBOARD_PORT`)
- Controllare router `api-health-router` (priority 150)

## Contributors

Sviluppato da Team FisioRAG
