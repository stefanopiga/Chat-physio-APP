# FisioRAG - Documentazione Tecnica

> **Knowledge Hub** per sviluppo, architettura, testing e deployment del sistema FisioRAG.  
> **Ultima revisione**: 2025-01-17

---

## 🗂️ Struttura Documentazione

```
docs/
├── architecture/          # Architettura tecnica e addenda
├── prd/                   # Product Requirements (epics, features)
├── stories/               # User stories implementative
├── qa/                    # Quality assurance (gates, assessments)
├── operations/            # Deployment, monitoring, runbooks
├── troubleshooting/       # Guide risoluzione problemi
└── reports/               # Report tecnici e metriche
```

---

## 📚 Guide Principali

### Architettura & Design

| Documento | Descrizione | Quando Consultare |
|-----------|-------------|-------------------|
| **[Architecture Index](architecture/index.md)** | Indice completo architettura con tutti gli addenda | Overview sistema, entry point architettura |
| **[Tech Stack](architecture/sezione-3-tech-stack.md)** | Stack tecnologico completo e rationale scelte | Setup progetto, scelta tecnologie |
| **[Coding Standards](architecture/sezione-12-standard-di-codifica.md)** | Standard di codifica backend/frontend | Code review, best practices |
| **[Testing Strategy](architecture/sezione-11-strategia-di-testing.md)** | Strategia testing (unit/integration/e2e) | Scrittura test, copertura |

### Quick References

| Documento | Descrizione | Quando Consultare |
|-----------|-------------|-------------------|
| **[Pydantic Settings Quick Ref](pydantic-settings-quick-reference.md)** | Pattern configuration management | Implementazione config, validators, secrets |
| **[FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md)** | Pattern endpoint sicuri e performanti | Sviluppo API, autenticazione, error handling |
| **[LangChain RAG Patterns](architecture/addendum-langchain-rag-debug-patterns.md)** | Pattern RAG con LangChain | Implementazione RAG, debugging retrieval |

### Product & Stories

| Documento | Descrizione | Quando Consultare |
|-----------|-------------|-------------------|
| **[PRD Index](prd/index.md)** | Product Requirements Documents | Requisiti business, scope features |
| **[Stories](stories/)** | User stories implementative | Implementazione features, acceptance criteria |

---

## 🎯 Quick Start per Ruolo

### 👨‍💻 Developer

**Setup iniziale:**
1. [Tech Stack](architecture/sezione-3-tech-stack.md) → capire tecnologie usate
2. [Unified Project Structure](architecture/sezione-7-struttura-unificata-del-progetto.md) → organizzazione codebase
3. [Coding Standards](architecture/sezione-12-standard-di-codifica.md) → standard backend/frontend
4. `ENV_TEMPLATE.txt` → configurazione locale

**Implementazione feature:**
1. Leggere story in `stories/` → requisiti e acceptance criteria
2. Consultare addenda rilevanti:
   - [FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md) → endpoint API
   - [Pydantic Settings](pydantic-settings-quick-reference.md) → configurazione
   - [LangChain Patterns](architecture/addendum-langchain-rag-debug-patterns.md) → RAG
3. [Testing Strategy](architecture/sezione-11-strategia-di-testing.md) → approccio testing

**Troubleshooting:**
- `troubleshooting/` → guide risoluzione problemi comuni
- `reports/` → report debug e metriche

---

### 🏗️ Architect

**Design decisions:**
1. [Architecture Index](architecture/index.md) → stato attuale architettura
2. [High-Level Architecture](architecture/sezione-2-architettura-di-alto-livello.md) → componenti sistema
3. [Data Models](architecture/sezione-4-modelli-di-dati.md) → schema database
4. [Security & Performance](architecture/sezione-10-sicurezza-e-performance.md) → NFR

**Addenda tecnici:**
- [Enterprise Standards](architecture/addendum-enterprise-standards.md) → SLO/SLI, threat modeling
- [External Services Error Handling](architecture/addendum-external-services-error-handling.md) → resilienza
- [Security Standards Compliance](architecture/addendum-security-standards-compliance.md) → compliance

---

### 🧪 QA / Test Engineer

**Setup testing:**
1. [Testing Strategy](architecture/sezione-11-strategia-di-testing.md) → overview approccio
2. [Backend Testing](architecture/addendum-testing-backend-4.1.md) → pytest patterns
3. Story → sezione "Testing" → test cases specifici

**Quality gates:**
- `qa/gates/` → decisioni quality gate per story
- `qa/assessments/` → risk profiles, NFR assessments, trace matrices

**Metriche:**
- `reports/` → report performance, coverage, resilience

---

### 📋 Product Manager

**Requisiti e planning:**
1. [PRD Index](prd/index.md) → product requirements
2. `stories/` → breakdown features in user stories

**Status implementazione:**
- Story status: Draft / Ready / InProgress / Review / Done
- `qa/gates/` → quality status (PASS/CONCERNS/FAIL)

---

## 🔥 Hot Topics / Aggiornamenti Recenti

| Data | Topic | Documenti Rilevanti |
|------|-------|---------------------|
| 2025-01-17 | **Pydantic Settings Integration** | [Addendum Pydantic Settings](architecture/addendum-pydantic-settings-configuration.md), [Quick Ref](pydantic-settings-quick-reference.md), [Story 2.12](stories/2.12.gpt-5-nano-integration.md) |
| 2025-10-14 | Classification Cache & HNSW Tuning | [Story 2.9](stories/2.9.classification-cache.md), [Addendum HNSW](architecture/addendum-hnsw-params-and-async.md) |
| 2025-10-08 | JWT RFC Compliance | [FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md) (v1.1) |

---

## 📖 Convenzioni Documentazione

### Formato File

- **Architecture**: Markdown con code blocks e diagrammi Mermaid
- **Stories**: Template YAML-based con sezioni standardizzate
- **QA Gates**: YAML structured con decision rationale

### Naming Conventions

- **Stories**: `{epic}.{story}.{slug}.md` (es. `2.12.gpt-5-nano-integration.md`)
- **Addenda**: `addendum-{topic}.md` (es. `addendum-pydantic-settings-configuration.md`)
- **Gates**: `{epic}.{story}-{slug}.yml` (es. `2.12-gpt-5-nano-integration.yml`)
- **Assessments**: `{epic}.{story}-{type}-{YYYYMMDD}.md` (es. `2.12-risk-20250117.md`)

### Status Values

**Story Status:**
- `Draft` → in preparazione
- `Ready` → pronta per implementazione
- `InProgress` → in sviluppo
- `Review` → in revisione QA
- `Done` → completata e validata

**Gate Status:**
- `PASS` → quality gate superato
- `CONCERNS` → issue non bloccanti
- `FAIL` → issue bloccanti
- `WAIVED` → issue accettati con waiver

---

## 🔍 Ricerca Documenti

### Per Topic

| Cerchi informazioni su... | Consulta |
|----------------------------|----------|
| **Configuration management** | [Pydantic Settings Quick Ref](pydantic-settings-quick-reference.md), [Addendum completo](architecture/addendum-pydantic-settings-configuration.md) |
| **API development** | [FastAPI Best Practices](architecture/addendum-fastapi-best-practices.md) |
| **RAG implementation** | [LangChain RAG Patterns](architecture/addendum-langchain-rag-debug-patterns.md), [PGVector Integration](architecture/addendum-pgvector-langchain-supabase.md) |
| **Authentication** | [Student Access Code System](architecture/addendum-1.3-student-access-code-system.md), [FastAPI JWT patterns](architecture/addendum-fastapi-best-practices.md) |
| **Frontend components** | [Shadcn/UI Registry](architecture/addendum-shadcn-components-registry.md), [Tailwind Setup](architecture/addendum-tailwind-shadcn-setup.md) |
| **Database** | [Data Models](architecture/sezione-4-modelli-di-dati.md), [asyncpg Pattern](architecture/addendum-asyncpg-database-pattern.md) |
| **Testing** | [Testing Strategy](architecture/sezione-11-strategia-di-testing.md), [Backend Testing](architecture/addendum-testing-backend-4.1.md) |
| **Deployment** | [Deployment Architecture](architecture/sezione-9-architettura-di-deployment.md) |
| **Monitoring** | [Monitoring & Observability](architecture/sezione-14-monitoraggio-e-osservabilit.md) |

### Per Tecnologia

- **FastAPI** → [Best Practices](architecture/addendum-fastapi-best-practices.md), [Error Handling](architecture/sezione-13-strategia-di-gestione-degli-errori.md)
- **Pydantic** → [Settings Quick Ref](pydantic-settings-quick-reference.md), [Settings Addendum](architecture/addendum-pydantic-settings-configuration.md)
- **LangChain** → [RAG Patterns](architecture/addendum-langchain-rag-debug-patterns.md), [Loaders & Splitters](architecture/addendum-langchain-loaders-splitters.md)
- **React/Shadcn** → [Components Registry](architecture/addendum-shadcn-components-registry.md), [Dialog Implementation](architecture/addendum-shadcn-dialog-implementation.md)
- **Supabase** → [PGVector Integration](architecture/addendum-pgvector-langchain-supabase.md)

---

## 🆘 Supporto

**Problemi comuni:**
- Consulta `troubleshooting/` per guide specifiche
- Verifica `reports/` per report debug recenti
- Controlla story correlata per Dev Notes e Debug Log

**Escalation:**
1. Architect → design decisions, architettura
2. QA → quality gates, risk assessment
3. PM → requisiti, priorità

---

## 📝 Contribuire alla Documentazione

**Principi:**
- Documentazione vive con il codice
- Aggiornare documentazione contestualmente a implementazione
- Usare template standardizzati (story, addenda, gates)

**Workflow:**
1. Implementi feature → aggiorni story (Dev Agent Record)
2. QA review → crea gate file
3. Pattern riutilizzabili → crea/aggiorna addendum
4. Breaking changes → aggiorna Architecture Index

---

**Ultima revisione**: 2025-01-17  
**Maintainer**: Architecture Team  
**Versione documentazione**: 2.12+

