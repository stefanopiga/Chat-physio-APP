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

## Testing

### Unit Tests (Vitest)

I test unitari sono in `src/**/__tests__/*.test.tsx`:
- Component rendering
- Business logic
- API client functions

Configurazione in `vitest.setup.ts` e `vite.config.ts`.

### E2E Tests (Playwright)

I test E2E sono in `tests/*.spec.ts`:
- User flows completi
- Accessibility checks
- Cross-browser testing

Configurazione in `playwright.config.ts`.

Report HTML disponibile in `playwright-report/` dopo esecuzione.

## Build e Deployment

### Build Produzione

```powershell
npm run build
```

Output ottimizzato in `dist/`:
- Assets con hash per caching
- Code splitting automatico
- Minification e tree-shaking

### Deployment Docker

Il frontend viene deployato tramite Nginx container:

```powershell
# Dalla root del progetto
docker compose up web --build
```

Dockerfile in `apps/web/Dockerfile`:
1. Build stage: compila app con Vite
2. Runtime stage: serve static files con Nginx

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

## Contributors

Sviluppato da Team FisioRAG
