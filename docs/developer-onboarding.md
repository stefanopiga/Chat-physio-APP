# Developer Onboarding Guide - FisioRAG

> Guida completa per developer che iniziano a lavorare sul progetto FisioRAG.  
> **Ultima revisione**: 2025-11-12

---

## 🎯 Obiettivi Onboarding

Al completamento di questa guida sarai in grado di:
- ✅ Setup completo ambiente di sviluppo locale
- ✅ Comprendere architettura e tech stack del progetto
- ✅ Navigare la codebase e documentazione efficacemente
- ✅ Implementare features seguendo standard e pattern del progetto
- ✅ Eseguire test e validare modifiche
- ✅ Contribuire al progetto con confidence

**Tempo stimato**: 2-4 ore

---

## 📋 Prerequisiti

### Software Richiesto

| Software | Versione Minima | Verifica | Installazione |
|----------|----------------|----------|---------------|
| **Node.js** | 18+ | `node --version` | [nodejs.org](https://nodejs.org/) |
| **PNPM** | 8.12+ | `pnpm --version` | `npm install -g pnpm` |
| **Python** | 3.11+ | `python --version` | [python.org](https://www.python.org/) |
| **Poetry** | 1.7+ | `poetry --version` | [python-poetry.org](https://python-poetry.org/) |
| **Docker** | 24+ | `docker --version` | [docker.com](https://www.docker.com/) |
| **Git** | 2.40+ | `git --version` | [git-scm.com](https://git-scm.com/) |

### Conoscenze Richieste

**Backend (Python/FastAPI)**:
- Python async/await
- FastAPI framework basics
- PostgreSQL & SQL queries
- RESTful API design

**Frontend (React/TypeScript)**:
- React Hooks (useState, useEffect, custom hooks)
- TypeScript basics
- Tailwind CSS
- Component-based architecture

**Infrastruttura**:
- Docker basics
- Environment variables
- Git workflow

---

## 🚀 Setup Ambiente (30-45 min)

### 1. Clone Repository

```bash
git clone <repository-url>
cd fisio-rag-master/APPLICAZIONE
```

### 2. Setup Backend (FastAPI)

```bash
cd apps/api

# Installa dependencies con Poetry
poetry install

# Attiva virtual environment
poetry shell

# Copia template environment variables
cp .env.example .env

# Configura .env con le credenziali necessarie
# (Vedi sezione "Configurazione Credenziali" sotto)
```

**Variabili ambiente critiche** (`.env`):
```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/fisiorag

# JWT
SUPABASE_JWT_SECRET=your_jwt_secret
```

### 3. Setup Frontend (React/Vite)

```bash
cd apps/web

# Installa dependencies con PNPM
pnpm install

# Copia template environment variables
cp .env.example .env

# Configura variabili ambiente frontend
```

**Variabili ambiente frontend** (`.env`):
```bash
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_anon_key
VITE_API_BASE_URL=http://localhost:8000
```

**📖 Tech Reference**: [Vite Environment Variables](tech-reference/06-vite-environment-variables.md) — Guida completa su `VITE_` prefix, modes, TypeScript types, security best practices.

### 4. Setup Database (Supabase Local o Cloud)

**Opzione A: Supabase Cloud** (Raccomandato per quick start):
1. Crea account su [supabase.com](https://supabase.com)
2. Crea nuovo progetto
3. Copia credenziali in `.env` files
4. Esegui migrations: `cd supabase && supabase db push`

**Opzione B: Supabase Local** (Richiede Docker):
```bash
cd supabase
supabase start
# Segui output per credenziali locali
```

### 5. Verifica Setup

**Backend**:
```bash
cd apps/api
poetry run uvicorn api.main:app --reload
# Apri http://localhost:8000/docs per Swagger UI
```

**Frontend**:
```bash
cd apps/web
pnpm dev
# Apri http://localhost:5173
```

**Health Check**:
- ✅ Backend Swagger UI visibile
- ✅ Frontend carica senza errori console
- ✅ Login admin funziona
- ✅ Chat interface risponde

---

## 📚 Documentazione Essenziale

### Architettura & Design

| Documento | Quando Leggerlo | Priorità |
|-----------|-----------------|----------|
| **[Architecture Index](architecture/index.md)** | Prima di iniziare qualsiasi feature | 🔴 Alta |
| **[Tech Stack](architecture/sezione-3-tech-stack.md)** | Durante setup, per comprendere tecnologie | 🔴 Alta |
| **[Project Structure](architecture/sezione-7-struttura-unificata-del-progetto.md)** | Per navigare codebase | 🔴 Alta |
| **[Coding Standards](architecture/sezione-12-standard-di-codifica.md)** | Prima di scrivere codice | 🔴 Alta |
| **[Testing Strategy](architecture/sezione-11-strategia-di-testing.md)** | Prima di scrivere test | 🟡 Media |

### Quick References

| Documento | Contenuto | Quando Usarlo |
|-----------|-----------|---------------|
| **[FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md)** | Pattern endpoint sicuri, JWT, rate limiting | Implementazione backend API |
| **[Pydantic Settings](pydantic-settings-quick-reference.md)** | Configuration management | Gestione configurazioni backend |
| **[LangChain RAG Patterns](architecture/addendum-langchain-rag-debug-patterns.md)** | RAG implementation patterns | Lavoro su retrieval/generation |

---

## 🛠️ Tech References - Pattern Implementativi

**Nuova risorsa**: La directory [`tech-reference/`](tech-reference/) contiene guide implementative dettagliate per librerie e pattern tecnici comuni.

### Backend Pattern

| Tech Reference | Contenuto | Quando Usare |
|----------------|-----------|--------------|
| **[Rate Limiting Backend](tech-reference/04-rate-limiting-backend.md)** | slowapi, Redis/Memory backends, decorator patterns | Implementazione rate limiting su endpoint FastAPI |
| **[PostgreSQL Pagination](tech-reference/05-postgresql-pagination.md)** | Keyset vs OFFSET pagination, performance trade-offs | Query liste con pagination efficiente |
| **[Exponential Backoff](tech-reference/03-exponential-backoff.md)** | node-retry, Retry-After header, best practices | Retry logic per chiamate API esterne |

### Frontend Pattern

| Tech Reference | Contenuto | Quando Usare |
|----------------|-----------|--------------|
| **[Virtual Scrolling](tech-reference/01-virtual-scrolling.md)** | react-window, TanStack Virtual, react-virtuoso | Rendering liste molto lunghe (>100 items) |
| **[Toast Notifications](tech-reference/02-toast-notifications.md)** | Sonner (shadcn/ui recommended) | Notifiche utente transient |
| **[Vite Environment Variables](tech-reference/06-vite-environment-variables.md)** | VITE_ prefix, modes, TypeScript types | Gestione env vars frontend |
| **[React Hook Testing](tech-reference/07-react-hook-testing.md)** | @testing-library/react-hooks, Vitest patterns | Testing custom hooks isolati |

**📁 Indice completo**: [`tech-reference/00-indice.md`](tech-reference/00-indice.md)

---

## 💻 Workflow Development

### 1. Scegliere una Story

```bash
# Consulta stories disponibili
ls docs/stories/

# Leggi story da implementare
# Esempio: docs/stories/9.2-session-history-retrieval-ui.md
```

**Story Structure**:
- **Acceptance Criteria**: Requisiti funzionali da soddisfare
- **Dev Notes**: Technical guidance, architecture references
- **Tasks/Subtasks**: Breakdown implementativo step-by-step
- **Testing**: Test requirements e acceptance

### 2. Branch Workflow

```bash
# Crea branch feature
git checkout -b feature/story-9.2-session-history

# Lavora su branch
# Commit frequenti con messaggi descrittivi
git add .
git commit -m "feat(story-9.2): implement backend GET history endpoint"

# Push branch
git push origin feature/story-9.2-session-history

# Apri PR quando ready
```

### 3. Implementation Workflow

**Backend Feature**:
```bash
cd apps/api

# 1. Crea/modifica file necessari
# 2. Segui pattern da addenda/tech-references
# 3. Implementa business logic
# 4. Aggiungi docstrings e type hints
# 5. Scrivi unit tests

# Run tests
poetry run pytest tests/
poetry run pytest --cov=api --cov-report=html

# Run linter
poetry run ruff check
```

**Frontend Feature**:
```bash
cd apps/web

# 1. Crea/modifica componenti
# 2. Segui Shadcn/UI patterns
# 3. Implementa custom hooks se necessario
# 4. Aggiungi TypeScript types
# 5. Scrivi unit tests

# Run tests
pnpm test
pnpm test:coverage

# Run linter
pnpm lint
```

### 4. Testing

**Unit Tests** (Backend):
```bash
cd apps/api
poetry run pytest tests/unit/
```

**Unit Tests** (Frontend):
```bash
cd apps/web
pnpm test
```

**Integration Tests** (Backend):
```bash
cd apps/api
poetry run pytest tests/integration/
```

**E2E Tests** (Frontend):
```bash
cd apps/web
pnpm test:e2e
```

**📖 Reference**: [Testing Strategy](architecture/sezione-11-strategia-di-testing.md)

### 5. Code Review Preparation

**Checklist prima di aprire PR**:
- [ ] Tutti test passano (unit + integration)
- [ ] Linter passa senza warnings
- [ ] Code coverage ≥ target (Backend 80%, Frontend 70%)
- [ ] Docstrings/comments aggiunti per logica complessa
- [ ] Story acceptance criteria soddisfatti
- [ ] File List in story aggiornato con file modificati
- [ ] Dev Agent Record aggiornato con completion notes

---

## 🎓 Learning Path per Nuovi Developer

### Week 1: Familiarizzazione

**Giorno 1-2: Setup e Documentazione**
- [ ] Completare setup ambiente
- [ ] Leggere Architecture Index e Tech Stack
- [ ] Esplorare codebase: `apps/api/`, `apps/web/`, `supabase/`
- [ ] Leggere Coding Standards e Project Structure

**Giorno 3-4: Simple Feature**
- [ ] Implementare small story (es. UI enhancement, bug fix)
- [ ] Seguire workflow development guidato
- [ ] Scrivere primi test
- [ ] Aprire prima PR

**Giorno 5: Code Review**
- [ ] Ricevere feedback su PR
- [ ] Applicare suggested changes
- [ ] Merge prima feature

### Week 2: Backend Deep Dive

**Giorno 1-2: FastAPI Patterns**
- [ ] Studiare [FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md)
- [ ] Implementare nuovo endpoint seguendo pattern
- [ ] Aggiungere rate limiting ([Tech Reference 04](tech-reference/04-rate-limiting-backend.md))
- [ ] Scrivere unit tests completi

**Giorno 3-4: Database & RAG**
- [ ] Studiare schema database
- [ ] Implementare query con pagination ([Tech Reference 05](tech-reference/05-postgresql-pagination.md))
- [ ] Esplorare RAG patterns ([LangChain RAG Debug](architecture/addendum-langchain-rag-debug-patterns.md))

**Giorno 5: Integration Tests**
- [ ] Scrivere integration tests per endpoint
- [ ] Verificare coverage ≥80%

### Week 3: Frontend Deep Dive

**Giorno 1-2: React & Shadcn/UI**
- [ ] Studiare [Shadcn Components Registry](architecture/addendum-shadcn-components-registry.md)
- [ ] Implementare nuovo component
- [ ] Integrare con Tailwind CSS
- [ ] Responsive design mobile-first

**Giorno 3-4: Hooks & State Management**
- [ ] Implementare custom hook
- [ ] Testing hooks ([Tech Reference 07](tech-reference/07-react-hook-testing.md))
- [ ] Integrare con API backend

**Giorno 5: E2E Tests**
- [ ] Scrivere Playwright E2E tests
- [ ] Test critical user flows

### Week 4: Full-Stack Feature

**Giorno 1-5: End-to-End Story**
- [ ] Implementare feature full-stack completa
- [ ] Backend endpoint + Frontend UI + Tests
- [ ] Seguire tutti standard e best practices
- [ ] Documentare pattern riutilizzabili
- [ ] Code review e merge

---

## 🔍 Troubleshooting Comune

### Backend

**Problem**: `poetry install` fails
```bash
# Solution: Update poetry
pip install --upgrade poetry
poetry cache clear . --all
poetry install
```

**Problem**: Database connection error
```bash
# Check .env DATABASE_URL
# Verify Supabase running (local) o credentials (cloud)
poetry run python -c "from api.core.config import settings; print(settings.database_url)"
```

**Problem**: Import errors
```bash
# Verify virtual environment attivo
poetry shell
# Reinstall dependencies
poetry install --sync
```

### Frontend

**Problem**: `pnpm dev` fails
```bash
# Clear cache e reinstall
rm -rf node_modules
pnpm install

# Check Node version
node --version  # Should be 18+
```

**Problem**: Vite environment variables not working
- **Soluzione**: Variabili devono avere prefix `VITE_`
- **Reference**: [Tech Reference 06](tech-reference/06-vite-environment-variables.md)

**Problem**: Shadcn/UI component import error
```bash
# Verify component installed
ls apps/web/src/components/ui/

# Reinstall component
pnpm dlx shadcn@latest add <component-name>
```

---

## 📞 Supporto & Risorse

### Documentazione Interna

- **Architecture**: [`docs/architecture/`](architecture/)
- **Stories**: [`docs/stories/`](stories/)
- **Tech References**: [`docs/tech-reference/`](tech-reference/)
- **QA Gates**: [`docs/qa/gates/`](qa/gates/)

### Link Utili

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **Supabase Docs**: https://supabase.com/docs
- **Shadcn/UI**: https://ui.shadcn.com/
- **Tailwind CSS**: https://tailwindcss.com/docs

### Getting Help

1. **Consulta documentazione** (`docs/` directory)
2. **Cerca in tech-reference** per pattern implementativi
3. **Leggi addenda architettura** per pattern avanzati
4. **Chiedi a team lead** se blocchi persistono

---

## ✅ Checklist Onboarding Completato

Quando puoi rispondere "Sì" a tutte queste domande, sei pronto per development autonomo:

- [ ] Ambiente di sviluppo funzionante (backend + frontend + database)
- [ ] Familiarità con tech stack (FastAPI, React, Supabase)
- [ ] Compreso workflow development (branch, commit, PR)
- [ ] Implementata almeno 1 feature full-stack end-to-end
- [ ] Scritti test unit + integration + E2E
- [ ] Letto e compreso Coding Standards
- [ ] Familiarità con tech-reference per pattern comuni
- [ ] PR merged dopo code review

---

## 🎉 Welcome to the Team!

Ora sei pronto per contribuire efficacemente al progetto FisioRAG. Ricorda:

- ✓ **Consulta sempre documentazione** prima di implementare
- ✓ **Segui standard e pattern** del progetto
- ✓ **Scrivi test completi** per ogni feature
- ✓ **Chiedi chiarimenti** quando necessario
- ✓ **Documenta decisioni** tecniche importanti
- ✓ **Condividi knowledge** con il team

**Buon coding! 🚀**

---

**Ultima revisione**: 2025-11-12  
**Maintainer**: Architecture Team  
**Feedback**: Suggerimenti di miglioramento sempre benvenuti


