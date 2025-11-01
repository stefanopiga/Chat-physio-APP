# FisioRAG Brownfield Architecture Document

## Introduction

Questo documento descrive lo stato ATTUALE del codice e delle configurazioni presenti nella cartella `APPLICAZIONE` del monorepo.

### Document Scope

Comprehensive documentation of entire system.

### Change Log

| Date       | Version | Description                 | Author |
| ---------- | ------- | --------------------------- | ------ |
| 2025-09-16 | 1.0     | Initial brownfield analysis | not available in source |
## Quick Reference - Key Files and Entry Points

### Frontend (apps/web)
- Entry: `apps/web/src/main.tsx`
```text
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```
- Router/UI: `apps/web/src/App.tsx`
```text
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
...
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/" element={<AccessCodePage />} />
  <Route path="/dashboard" element={<AuthGuard><DashboardPage /></AuthGuard>} />
  <Route path="/chat" element={<div>Chat</div>} />
</Routes>
```
- Test setup: `apps/web/vite.config.ts` (Vitest jsdom, setupFiles `./vitest.setup.ts`)

### Backend (apps/api)
- API: `apps/api/api/main.py`
```text
@app.get("/health")
...
@app.post("/api/v1/admin/access-codes/generate")
...
@app.post("/api/v1/auth/exchange-code")
```
- JWT: richiede `SUPABASE_JWT_SECRET` e verifica `aud=authenticated`.

### Tooling & Infra
- Compose: `docker-compose.yml` (traefik proxy, api, web)
- FE pkg: `apps/web/package.json` (react 19, react-router-dom 7, supabase-js 2)
- BE deps: `apps/api/pyproject.toml` (fastapi, uvicorn, pyjwt)
## High Level Architecture

### Technical Summary
- Frontend: React + TypeScript + Vite (Vitest, Playwright). Router presente, guard `AuthGuard` lato FE.
- Backend: FastAPI con CORS aperto per dev, logging JSON, autenticazione Bearer JWT (HS256) con secret `SUPABASE_JWT_SECRET`.
- Access Codes: generazione (admin, protetto) e scambio codice→JWT temporaneo.
- Reverse Proxy: Traefik (rule Host(`localhost`) con PathPrefix per `/api`).

### Actual Tech Stack
| Category | Technology | Version | Notes |
| :--- | :--- | :--- | :--- |
| FE Framework | React | ^19.1.1 | `apps/web/package.json` |
| Router | react-router-dom | ^7.8.2 | Router v7, `BrowserRouter` |
| FE Build | Vite | ^5.4.20 | Vitest config jsdom |
| FE Testing | Vitest/RTL/Playwright | see devDeps | jsdom + setupFiles |
| Auth SDK | @supabase/supabase-js | ^2.57.4 | package.json |
| BE Framework | FastAPI | ^0.116.1 | pyproject.toml |
| JWT | PyJWT | ^2.10.1 | HS256, aud=authenticated |
| Server | Uvicorn | ^0.35.0 | pyproject.toml |
| Orchestration | Docker Compose | latest | `docker-compose.yml` |
| Proxy | Traefik | v3.1 | rules per api/web |
## Source Tree and Module Organization (Actual)

- Monorepo: `apps/web`, `apps/api`, `docs`, `packages`, root compose.
- FE Entry: `apps/web/src/main.tsx`; routing e guardie in `apps/web/src/App.tsx`.
- BE API: `apps/api/api/main.py` con endpoint `health`, `admin/access-codes/generate`, `auth/exchange-code`.

## Data Models and APIs

- OpenAPI: not available in source.
- Endpoint principali:
  - `GET /health`: healthcheck.
  - `POST /api/v1/admin/access-codes/generate`: genera codice (Bearer admin richiesto).
  - `POST /api/v1/auth/exchange-code`: scambio codice per JWT temporaneo.

## Technical Debt and Known Issues

- FE routing: le route richieste dalla story 1.4 nel PRD (`/admin/dashboard`, `/chat`) non corrispondono esattamente a `App.tsx` (`/dashboard`, `/chat`) e placeholder admin/student non standardizzati. Fonte: `apps/web/src/App.tsx`.
- Auth FE: presenza di `AuthGuard` ma assenza di integrazione visibile con `@supabase/supabase-js` negli import letti. Fonte: `apps/web/src/App.tsx` e `apps/web/package.json`.
- BE security: CORS `*` per dev; assenza di RLS esplicita lato documento API. Fonte: `apps/api/api/main.py`.
- OpenAPI mancante: `docs/api/openapi.yml` non presente (stated in arch doc, ma non trovato nei file letti). Fonte: `docs/architecture/sezione-7-struttura-unificata-del-progetto.md` vs workspace.

## Development and Deployment

### Local Development Setup
- Compose con Traefik, `api`, `web`. Variabili: `SUPABASE_JWT_SECRET` richiesta all'avvio backend. Fonte: `docker-compose.yml`, `apps/api/api/main.py`.

### Build and Deployment Process
- FE: `pnpm build` (da package.json). Test: `pnpm test`, E2E: `pnpm test:e2e`.
- BE: esecuzione uvicorn nel Dockerfile (non letto qui), dipendenze Poetry in `pyproject.toml`.

## Testing Reality

- FE: Vitest jsdom, setup `vitest.setup.ts`. E2E con Playwright (config presente).
- BE: pytest in `pyproject.toml` (dev group). Copertura non rilevata nei file letti.
