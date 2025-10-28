# FisioRAG

Sistema RAG (Retrieval-Augmented Generation) per assistenza studenti di fisioterapia basato su documentazione scientifica e linee guida cliniche.

## Architettura

Monorepo organizzato in:
- **apps/api**: Backend FastAPI + Celery + Redis
- **apps/web**: Frontend React + TypeScript + Vite + Shadcn/UI
- **supabase**: Database PostgreSQL + PGVector per embeddings
- **scripts**: Script operazionali per amministrazione e ingestion

## Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 18+
- Docker Desktop
- Account Supabase (o istanza locale)

### Setup Ambiente

1. Clonare il repository
```powershell
git clone <repository-url>
cd APPLICAZIONE
```

2. Configurare variabili d'ambiente
```powershell
Copy-Item .env.example .env
# Editare .env con credenziali Supabase e OpenAI
```

3. Avviare i servizi
```powershell
docker compose up --build -d
```

4. Verificare disponibilità
```powershell
# Health check API
curl http://localhost/health

# Health check frontend
curl http://localhost
```

### Primo Avvio

Il sistema sarà disponibile su:
- Frontend: http://localhost
- API: http://localhost/api
- Traefik Dashboard: http://localhost:18080

## Struttura Progetto

```
apps/
├── api/              # Backend FastAPI
│   ├── api/          # Codice sorgente
│   ├── tests/        # Test unitari e integration
│   └── ingestion/    # Pipeline ingestion documenti
├── web/              # Frontend React
│   ├── src/          # Codice sorgente
│   └── tests/        # Test Vitest + Playwright
conoscenza/           # Knowledge base documenti (non versionato)
scripts/              # Script operazionali
supabase/             # Database migrations e schema
tests/                # Integration tests cross-app
```

### Note sulla Struttura
- La cartella `conoscenza/` contiene la knowledge base locale e non è versionata (esclusa da .gitignore)
- I documenti della knowledge base possono essere organizzati in sottocartelle tematiche
- L'ingestion dei documenti avviene tramite script in `scripts/ingestion/` o API admin

## Comandi Comuni

### Sviluppo

```powershell
# Avvio ambiente development (con hot-reload)
docker compose -f docker-compose.dev.yml up

# Stop servizi
docker compose down

# Rebuild dopo modifiche Dockerfile
docker compose up --build
```

### Testing

```powershell
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

```powershell
# Deploy produzione
docker compose up --build -d

# View logs
docker compose logs -f

# Stop e cleanup
docker compose down -v
```

## Documentazione

La documentazione completa è disponibile nella cartella `docs/` (non versionata, consultare localmente):
- Architecture & Design
- API Specifications
- Testing Strategy
- Deployment Guide
- Operations & Troubleshooting

**Nota**: La cartella `docs/` è esclusa dal repository per mantenere la documentazione sincronizzata con l'ambiente locale di sviluppo.

## Variabili d'Ambiente Richieste

Le variabili essenziali da configurare in `.env`:

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
```

Consultare `ISTRUZIONI-USO-VARIABILI-AMBIENTE.md` per la guida completa.

## Troubleshooting

### Errore: "Container fails to start"
Verificare configurazione `.env` e credenziali Supabase.

### Errore: "OpenAI API Error"
Controllare validità `OPENAI_API_KEY` e credito disponibile.

### Porta 80 occupata (Windows)
```powershell
# Identificare processo su porta 80
netstat -ano | findstr :80

# Terminare processo o modificare docker-compose.yml per usare porta alternativa
```

### Reset completo ambiente
```powershell
docker compose down -v
docker compose up --build
```

## Contributors

Sviluppato da Team FisioRAG

