# FisioRAG Frontend

Interfaccia web React per il sistema FisioRAG, costruita con TypeScript, Vite e Shadcn/UI.

## Descrizione

Frontend moderno per studenti di fisioterapia che fornisce:
- Chat interattiva con sistema RAG
- Visualizzazione documenti e chunks
- Gestione citazioni e feedback
- Dashboard amministrazione (admin only)
- Sistema autenticazione Supabase

## Tech Stack

- **React 19** - Framework UI
- **TypeScript** - Type safety
- **Vite 5** - Build tool e dev server
- **Tailwind CSS 4** - Styling
- **Shadcn/UI** - Component library
- **React Router 7** - Routing
- **Supabase JS** - Authentication & API client
- **Vitest** - Unit testing
- **Playwright** - E2E testing

## Setup Sviluppo Locale

### Prerequisiti

- Node.js 18+
- PNPM (o NPM)

### Installazione

```powershell
cd apps/web
npm install
```

### Configurazione Ambiente

Creare file `.env.local`:

```bash
VITE_SUPABASE_URL=<your-supabase-url>
VITE_SUPABASE_ANON_KEY=<your-anon-key>
VITE_API_BASE_URL=http://localhost/api
```

### Avvio Development Server

```powershell
npm run dev
```

L'applicazione sarà disponibile su http://localhost:5173

## Struttura Directory src/

```
src/
├── components/        # Componenti React riutilizzabili
│   ├── ui/           # Componenti Shadcn/UI base
│   ├── ChatInput.tsx
│   ├── ChatMessagesList.tsx
│   ├── ChunkCard.tsx
│   ├── CitationPopover.tsx
│   ├── FeedbackControls.tsx
│   └── ...
├── pages/            # Pagine applicazione (route)
│   ├── ChatPage.tsx
│   ├── LoginPage.tsx
│   ├── DocumentsPage.tsx
│   ├── AdminDebugPage.tsx
│   └── ...
├── services/         # API client e business logic
│   ├── authService.ts
│   └── ...
├── lib/              # Utilities e configurazioni
│   ├── apiClient.ts
│   ├── supabaseClient.ts
│   └── utils.ts
├── App.tsx           # Root component + routing
└── main.tsx          # Entry point
```

## Script NPM Disponibili

### Development

```powershell
npm run dev          # Avvia dev server con hot-reload
npm run preview      # Preview build produzione localmente
```

### Building

```powershell
npm run build        # Build produzione (type-check + vite build)
```

Output in `dist/` (escluso da git)

### Testing

```powershell
# Unit tests (Vitest)
npm test                    # Run tests in watch mode
npm run test:coverage       # Run tests with coverage report

# E2E tests (Playwright)
npm run test:e2e           # Run end-to-end tests
```

### Linting

```powershell
npm run lint         # ESLint check
```

---

## 🧪 Testing

### Unit Tests (Vitest)

**Location**: `src/**/__tests__/*.test.tsx`

**Tipo test:**
- Component rendering (React Testing Library)
- Business logic (pure functions)
- API client functions (mocked)

**Configurazione**:
- Setup: `vitest.setup.ts`
- Config: `vite.config.ts` (sezione `test`)

**Comandi:**
```powershell
npm test                    # Run in watch mode
npm run test:coverage       # Generate coverage report
```

**Coverage output**: `coverage/` (escluso da Git, vedere `.gitignore`)

**Coverage report**: `coverage/index.html` (aprire in browser)

### E2E Tests (Playwright)

**⚠️ Path verification completata:**

I test E2E sono in **`tests/*.spec.ts`** (cartella root `tests/` in `apps/web/`):
- User flows completi (login → chat → logout)
- Accessibility checks (WCAG AA compliance)
- Cross-browser testing (Chromium, Firefox, WebKit)

**Configurazione**: `playwright.config.ts`

**Comandi:**
```powershell
npm run test:e2e                # Run all E2E tests
npx playwright test             # Alternative command
npx playwright test --ui        # Interactive UI mode
npx playwright test --debug     # Debug mode
```

**Artifacts (esclusi da Git, vedere `.gitignore`):**

| Artifact | Location | Descrizione |
|----------|----------|-------------|
| **Playwright Report** | `playwright-report/` | HTML report interattivo con screenshots/video |
| **Test Results** | `test-results/` | Raw test results, screenshots failures |
| **Trace Files** | `test-results/*.zip` | Playwright traces per debugging |

**Aprire report dopo test:**
```powershell
npx playwright show-report
# Apre http://localhost:9323 con report interattivo
```

### CI Artifacts Upload

**CI workflow** (`.github/workflows/ci.yml`) dovrebbe uploadare test artifacts:

```yaml
# Esempio configurazione CI per frontend tests (da aggiungere)
- name: Run E2E tests
  run: pnpm --prefix apps/web test:e2e

- name: Upload Playwright report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: apps/web/playwright-report/
```

**Nota**: Testing automatizzato in CI attualmente non presente, solo linting. Considerare aggiunta test step.

---

## 🐳 Docker Deployment Context

### Servizio Web in docker-compose.yml

**File configurazione**: [`docker-compose.yml`](../../docker-compose.yml) (root del progetto)

**Definizione servizio `web`:**
```yaml
services:
  web:
    container_name: physio-rag-web
    build:
      context: .
      dockerfile: ./apps/web/Dockerfile
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.web-router.rule=Host(`localhost`)"
      - "traefik.http.routers.web-router.priority=1"
      - "traefik.http.services.web-service.loadbalancer.server.port=80"
    networks:
      - physio-rag-net
```

### Build Multi-Stage (Dockerfile)

**File**: [`apps/web/Dockerfile`](./Dockerfile)

**Stage 1: Build (Vite)**
```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install
COPY . .
RUN pnpm run build  # Output in dist/
```

**Stage 2: Runtime (Nginx)**
```dockerfile
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

**Vantaggi build multi-stage:**
- ✅ Immagine finale leggera (~20MB vs ~500MB con Node)
- ✅ Nessun tool di build in produzione
- ✅ Solo static files serviti da Nginx

### Traefik Routing

**Reverse Proxy**: Traefik gestisce routing HTTP per tutti i servizi.

**Configurazione frontend:**
- **Host Rule**: `Host('localhost')` - Cattura tutte le richieste a localhost
- **Priority**: `1` (bassa) - Catturato per ultimo (dopo API e health con priority 100+)
- **Porta esposta**: `80` (Nginx interno)
- **Porta pubblica**: `80` (Traefik proxy, mappata da docker-compose)

**Traefik Dashboard**: http://localhost:18080 (porta configurabile via env `TRAEFIK_DASHBOARD_PORT`)

**Routing priority:**
1. `/health` → API service (priority 150)
2. `/api/*` → API service (priority 100)
3. `/*` → Web frontend (priority 1) - Catch-all

**Deploy stack completo:**
```powershell
# Dalla root del progetto
docker compose up --build

# Solo frontend (richiede altri servizi già running)
docker compose up web --build
```

### Volume Mounts (Development)

**Nota importante**: Il Dockerfile attuale è **production-ready** con Nginx statico.

Per **hot-reload development**:
- Usare `npm run dev` localmente (Vite dev server su porta 5173)
- Oppure creare `docker-compose.dev.yml` con Vite dev server e volume mount:
  ```yaml
  web-dev:
    command: npm run dev
    volumes:
      - ./apps/web:/app  # Hot-reload source changes
    ports:
      - "5173:5173"
  ```

---

## 🔄 CI/CD Integration

### Pipeline GitHub Actions

**Workflow file**: [`../../.github/workflows/ci.yml`](../../.github/workflows/ci.yml)

**Job: lint** (validazione codice frontend)

```yaml
- name: Install pnpm
  uses: pnpm/action-setup@v2
  with:
    version: 8.12.0  # Versione locked per consistency

- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version-file: ".nvmrc"  # Node 18+ (vedi root .nvmrc)

- name: Install frontend dependencies
  run: pnpm install --prefix apps/web

- name: Run frontend linter
  run: pnpm --prefix apps/web lint
```

**Testing pipeline**:
- **Unit tests** (Vitest): Eseguiti localmente, da aggiungere in CI
- **E2E tests** (Playwright): Eseguiti localmente, da aggiungere in CI

**Build verification**:
- Non presente in CI attuale, considerare aggiunta:
  ```yaml
  - name: Build frontend
    run: pnpm --prefix apps/web build
  ```

### Dependencies Management

**Package manager**: PNPM 8.12.0 (locked version in CI)

**Lock files**:
- `pnpm-lock.yaml` - Committato in repository per build reproducibili
- `package.json` - Dipendenze e scripts

**Aggiornamento dipendenze**:
```powershell
# Update all dependencies
pnpm update

# Update specific package
pnpm update react react-dom

# Check outdated packages
pnpm outdated
```

---

## 🔐 Environment Variables

### Complete VITE_* Variables Mapping

**Vite** espone solo variabili con prefisso `VITE_*` al bundle frontend (accessible via `import.meta.env`).

**File configurazione locale**: `.env.local` (creare da template se esiste `ENV_WEB_TEMPLATE.txt`)

**Variabili richieste:**

```bash
# Supabase Configuration (PUBLIC - safe for frontend)
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-key>  # ⚠️ ANON key, NOT service_role

# Backend API Base URL
VITE_API_BASE_URL=http://localhost/api  # Development (via Traefik proxy)
# VITE_API_BASE_URL=https://api.fisiorag.com/api  # Production
```

**⚠️ Security Critical:**

❌ **MAI includere `SUPABASE_SERVICE_ROLE_KEY` in variabili `VITE_*`**
- Le variabili `VITE_*` sono **embed nel bundle JavaScript** e visibili a tutti
- Usa solo `VITE_SUPABASE_ANON_KEY` (limited by Row Level Security)
- Backend usa `SUPABASE_SERVICE_ROLE_KEY` (mai esposto al frontend)

**Riferimenti:**
- Root: [`ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) - Guida completa variabili progetto
- Supabase: [`supabase/README.md`](../../supabase/README.md#-security--connection-details) - Security best practices

### Development vs Production Variables

**Development** (`.env.local`):
```bash
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<dev-anon-key>
VITE_API_BASE_URL=http://localhost/api  # Via Traefik proxy
```

**Production** (configurare in hosting/CI):
```bash
VITE_SUPABASE_URL=https://<prod-project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<prod-anon-key>
VITE_API_BASE_URL=https://api.fisiorag.com/api
```

**Build-time injection**:
- Variabili `VITE_*` sono sostituite durante `npm run build`
- Valori diversi per dev/prod gestiti tramite file `.env.local` / `.env.production`

---

## Build e Deployment

### Build Produzione

```powershell
npm run build
```

Output ottimizzato in `dist/`:
- Assets con hash per caching (es. `index-a3b2c1d.js`)
- Code splitting automatico (lazy loading routes)
- Minification e tree-shaking
- Source maps per debugging (opzionali)

**Nota**: La cartella `dist/` è esclusa da Git (vedi `.gitignore`).

### Deployment Docker

Il frontend viene deployato tramite Nginx container (vedere sezione Docker Deployment Context sopra).

```powershell
# Dalla root del progetto
docker compose up web --build
```

Dockerfile in `apps/web/Dockerfile`:
1. **Build stage**: compila app con Vite
2. **Runtime stage**: serve static files con Nginx

## Integrazione con API Backend

Il frontend comunica con il backend FastAPI tramite:

1. **API Client** (`lib/apiClient.ts`):
   - Base URL configurabile via env
   - Automatic JWT token injection
   - Error handling standardizzato

2. **Endpoints principali**:
   - `POST /api/v1/chat/sessions/:id/messages` - Invio messaggio chat
   - `GET /api/v1/admin/documents` - Lista documenti (admin)
   - `POST /api/v1/chat/messages/:id/feedback` - Feedback messaggi

3. **Authentication**:
   - Gestita da Supabase (`lib/supabaseClient.ts`)
   - JWT token automaticamente incluso nelle richieste
   - Protected routes con `AuthGuard.tsx` e `AdminGuard.tsx`

## Routing

Routes principali (vedi `App.tsx`):

- `/` - Chat page (public dopo login)
- `/login` - Login page
- `/admin/dashboard` - Admin dashboard (admin only)
- `/admin/documents` - Gestione documenti (admin only)
- `/admin/debug` - Debug tools (admin only)

## Convenzioni

### Componenti

- PascalCase per nomi file e componenti
- Props interface: `ComponentNameProps`
- Default export per componenti page
- Named export per utility components

### Stile

- Tailwind utility classes
- Shadcn/UI per componenti base
- Varianti gestite con `class-variance-authority`

### Testing

- Test file: `__tests__/ComponentName.test.tsx`
- E2E test: `tests/feature-name.spec.ts`
- Mock API calls in unit tests
- Use real API in E2E tests

---

## 📂 .gitignore Compliance

### Cartelle Escluse da Git (NO README dedicati)

**Importante**: Le seguenti cartelle sono **escluse da Git** (vedi [`.gitignore`](../../.gitignore)) e **NON devono avere README dedicati**:

| Cartella | Tipo | Motivo Esclusione |
|----------|------|-------------------|
| `node_modules/` | Dependencies | Package manager artifacts (PNPM/NPM) |
| `dist/` | Build Output | Generated da `npm run build` |
| `coverage/` | Test Artifacts | Vitest coverage reports |
| `playwright-report/` | Test Artifacts | Playwright HTML reports |
| `test-results/` | Test Artifacts | Playwright test results e traces |
| `.vite/` | Cache | Vite dev server cache |

**Best Practice**:
- ✅ Documentare comandi per generare questi artifacts (già fatto sopra)
- ❌ NON creare README.md dentro queste cartelle
- ✅ Verificare `.gitignore` prima di committare nuove cartelle

**Link relativi corretti**:
- Tutti i link relativi in questo README usano `../../` per root del progetto
- Esempio: [`docker-compose.yml`](../../docker-compose.yml) ✅
- ❌ NON usare path assoluti o path Windows (`C:\...`)

---

## Troubleshooting

### Errore: "Cannot find module"
```powershell
# Reinstallare dipendenze
Remove-Item -Recurse -Force node_modules
npm install
```

### Build fallisce
```powershell
# Verificare TypeScript errors
npx tsc --noEmit
```

### Hot reload non funziona
Verificare configurazione Vite in `vite.config.ts` e porte disponibili.

### Test E2E falliscono
```powershell
# Installare browser Playwright
npx playwright install
```

## Note Tecniche

### Vite Configuration

`vite.config.ts` configura:
- React plugin con Fast Refresh
- Path aliases (`@/` → `src/`)
- Proxy API per development
- Test environment (Vitest)

### Tailwind CSS

Configurazione in `tailwind.config.js`:
- Tailwind CSS v4
- Integrazione Shadcn/UI theme
- Custom animations (tw-animate-css)

### TypeScript

Configurazione split in:
- `tsconfig.json` - Config base
- `tsconfig.app.json` - App source code
- `tsconfig.node.json` - Build scripts (Vite)

---

## 📚 Cross-References

### Documentazione Correlata

| Documento | Descrizione | Link |
|-----------|-------------|------|
| **Architecture Docs** | Design system, patterns, best practices | [`../../docs/architecture/`](../../docs/architecture/) |
| **Frontend Architecture** | Component structure, state management | [`../../docs/architecture/sezione-6-frontend-architecture.md`](../../docs/architecture/) |
| **Backend API Docs** | API endpoints, authentication | [`../api/README.md`](../api/README.md) |
| **Database Schema** | Supabase schema, migrations, PGVector | [`../../supabase/README.md`](../../supabase/README.md) |
| **Environment Variables** | Complete .env guide | [`../../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md`](../../ISTRUZIONI-USO-VARIABILI-AMBIENTE.md) |
| **Docker Compose** | Full deployment stack | [`../../docker-compose.yml`](../../docker-compose.yml) |

### Altre Risorse

- **CI/CD Pipeline**: Vedere [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)
- **Testing Strategy**: Vedere [`docs/architecture/sezione-11-strategia-di-testing.md`](../../docs/architecture/sezione-11-strategia-di-testing.md)
- **Quality Gates**: Vedere [`docs/qa/gates/`](../../docs/qa/gates/)

---

## Contributors

Sviluppato da Team FisioRAG
