# FisioRAG Frontend Architecture Document

> Single source of truth for the web app’s UI architecture. Reflects the actual repository state (Vite + React 19 + React Router 7 + Tailwind v4 + Shadcn/Radix + Recharts + Supabase JS v2) and links to official references to avoid ambiguity across major versions.

## Change Log

| Date | Version | Description | Author |
| :--- | :--- | :--- | :--- |
| 2025-10-30 | 2.0 | Initial consolidation for React 19/Router 7/Tailwind 4; sections pre-filled and linked to official docs | Architecture

---

## Template and Framework Selection

- Existing codebase: Vite monorepo app at `apps/web/` using React 19, React Router 7, Tailwind CSS v4, Recharts, Supabase JS v2, and Shadcn-style UI components over Radix primitives.
- Constraints from the existing setup:
  - Build: Vite 5 with `@vitejs/plugin-react` and `@tailwindcss/vite`.
  - Path alias `@` configured in `vite.config.ts` and `tsconfig.json`.
  - Styling via Tailwind v4 `@import "tailwindcss";` (no classic tailwind.config.js) and design tokens in `src/index.css`.
  - Auth via Supabase JS v2; app-level API client handles token refresh on 401.
  - Analytics UI uses Recharts 3 with `ResponsiveContainer` and Tailwind utility classes for layout.

References
- Vite: https://vite.dev/guide/ and Env/Modes: https://vite.dev/guide/env-and-mode
- React 19: https://react.dev
- React Router 7: https://reactrouter.com
- Tailwind CSS v4 + Vite plugin: https://tailwindcss.com/docs/installation
- Shadcn UI: https://ui.shadcn.com
- Radix UI: https://www.radix-ui.com/primitives/docs
- Recharts: https://recharts.org
- Supabase JS v2: https://supabase.com/docs/reference/javascript

---

## Frontend Tech Stack

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| Framework | React | ^19.1.1 | UI library | Current repo version; aligns with modern React features. |
| UI Library | Shadcn UI + Radix | latest | Accessible primitives & composable UI | Lightweight, unopinionated theming with Tailwind. |
| State Management | Local state + service modules | n/a | Keep complexity low | No global state lib in repo; simple services suffice. |
| Routing | React Router | ^7.8.2 | Client routing | Matches code in `App.tsx`; guards via components. |
| Build Tool | Vite | ^5.4.20 | Dev/build tooling | Fast HMR; official React plugin used. |
| Styling | Tailwind CSS | ^4.1.13 | Utility-first CSS | v4 plugin flow; tokens in `index.css`. |
| Testing | Vitest + RTL + Playwright | latest | Unit/Integration/E2E | Matches project scripts and setup. |
| Component Library | Custom + Shadcn UI | latest | Cards, inputs, dialogs | Coherent with Tailwind and Radix. |
| Form Handling | Native/controlled inputs | n/a | Simple forms | Keep deps minimal until complexity grows. |
| Animation | Tailwind + tw-animate-css | latest | Lightweight transitions | Already present in `index.css`. |
| Dev Tools | ESLint | ^9.33.0 | Linting | Align with TypeScript/React 19. |

Notes
- Versions reflect `apps/web/package.json` at time of writing.
- If introducing global state later (e.g., Zustand), update this table and add patterns.

---

## Project Structure

Top-level (frontend): `apps/web/`

Key directories
- `src/pages/` – route-level pages (e.g., `AnalyticsPage.tsx`, `ChatPage.tsx`).
- `src/components/` – shared UI (guards, inputs, Shadcn-styled components).
- `src/components/ui/` – Shadcn-style primitives (button, card, dialog, etc.).
- `src/lib/` – service and client utilities (e.g., `apiClient.ts`, `supabaseClient.ts`).
- `src/index.css` – Tailwind v4 import and theme tokens (CSS variables) for light/dark.

TypeScript path alias
- `@/*` → `./src/*` (configured in `vite.config.ts` and `tsconfig.json`).

---

## State Management

Approach
- Prefer local component state and small service modules (e.g., `apiClient`, `authService`).
- Derive UI state from server responses where possible; avoid unnecessary global stores.

Guidelines
- Lift state up only when shared; otherwise keep it local to reduce re-renders.
- Memoize expensive derived data with `useMemo`; use `React.memo` for pure components rendering large lists.

---

## API Integration

Service Pattern
- Centralized `apiClient` wraps fetch with:
  - Bearer token from Supabase session or `sessionStorage` fallback.
  - 401 auto-refresh via `/api/v1/auth/refresh-token` and retry.
  - Typed request/response helpers for POST/GET.

Templates (TypeScript)
```ts
// apiClient.ts (excerpt)
const API_BASE = "/api/v1";

async function getAccessToken(): Promise<string> { /* Supabase session, then sessionStorage fallback */ }
async function refreshAccessToken(): Promise<string | null> { /* POST /auth/refresh-token with credentials: 'include' */ }

export const apiClient = {
  async get<T>(endpoint: string): Promise<T> { /* attach Authorization; handle 401 retry */ },
  async post<TReq, TRes>(endpoint: string, body: TReq): Promise<TRes> { /* typed post + 401 retry */ },
};
```

Supabase Client
```ts
// supabaseClient.ts (excerpt)
import { createClient } from "@supabase/supabase-js";
export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
  { auth: { autoRefreshToken: false, persistSession: true, detectSessionInUrl: true } }
);
```

References
- Supabase JS v2: sessions/auth: https://supabase.com/docs/reference/javascript/auth-signinwithpassword
- Vite env: https://vite.dev/guide/env-and-mode

---

## Routing

Pattern
- `BrowserRouter` at app root; routes under `Routes/Route` with component guards.
- Admin-only pages wrapped in `AdminGuard`; authenticated pages wrapped in `AuthGuard`.

Example
```tsx
<Router>
  <Routes>
    <Route path="/" element={<AccessCodePage />} />
    <Route path="/chat" element={<AuthGuard><ChatPage /></AuthGuard>} />
    <Route path="/admin/analytics" element={<AdminGuard><AnalyticsPage /></AdminGuard>} />
  </Routes>
</Router>
```

References
- React Router 7: https://reactrouter.com

---

## Styling Guidelines

Approach
- Tailwind CSS v4 with `@tailwindcss/vite` plugin; import once in `src/index.css`.
- Design tokens via CSS variables for color, spacing, typography, and dark mode.
- Shadcn-styled components under `src/components/ui/` with Radix primitives.

Example
```css
/* index.css */
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));
:root { /* CSS variables for theme */ }
.dark { /* inverted variables */ }
```

References
- Tailwind v4 install: https://tailwindcss.com/docs/installation
- Shadcn: https://ui.shadcn.com
- Radix: https://www.radix-ui.com/primitives/docs

---

## Charts (Recharts)

Guidelines
- Use `ResponsiveContainer` and ensure parent has an explicit height.
- Import named components (tree-shaking friendly): `import { BarChart, Bar, XAxis, ... } from 'recharts'`.
- Keep chart data typed (e.g., `{ name: string; count: number }`).

Example (Feedback)
```tsx
<div className="h-[300px]">
  <ResponsiveContainer width="100%" height="100%">
    <BarChart data={[{ name: 'Thumbs Up', count: 12 }, { name: 'Thumbs Down', count: 3 }] }>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Bar dataKey="count" fill="#22c55e" radius={[8,8,0,0]} />
    </BarChart>
  </ResponsiveContainer>
}</div>
```

References
- Recharts: https://recharts.org

---

## Testing Requirements

- Unit/Component: Vitest + React Testing Library.
- E2E: Playwright with accessibility checks via `@axe-core/playwright`.
- Target coverage: ~80% for new UI code; focus on critical flows.

Templates
```ts
// Component test
import { render, screen } from '@testing-library/react';
import AnalyticsPage from '@/pages/AnalyticsPage';
test('renders feedback ratio', () => {
  // mock auth + fetch
  render(<AnalyticsPage />);
  // assertions...
});
```

References
- Vitest: https://vitest.dev
- RTL: https://testing-library.com/docs/react-testing-library/intro
- Playwright: https://playwright.dev/docs/intro

---

## Environment Configuration

Vite runtime variables (build-time injected)
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_BASE_URL` (optional override; defaults to relative `""`)

Example `.env` (frontend)
```
VITE_SUPABASE_URL=https://<project>.supabase.co
VITE_SUPABASE_ANON_KEY=<anon-key>
VITE_API_BASE_URL=
```

References
- Vite env & modes: https://vite.dev/guide/env-and-mode
- Supabase configuration: https://supabase.com/docs/reference/javascript/initializing

---

## Frontend Developer Standards

Critical Rules
- Use `@` alias for internal imports; keep absolute paths consistent.
- Keep components pure; avoid side effects in render.
- Ensure parents of `ResponsiveContainer` have explicit height.
- Avoid wildcard imports for Recharts; import only used components.
- Keep auth/token logic centralized in `apiClient` and `authService`.

Quick Reference
- Dev: `pnpm -C apps/web dev`
- Build: `pnpm -C apps/web build`
- Unit tests: `pnpm -C apps/web test`
- E2E: `pnpm -C apps/web test:e2e`
- Path alias: `@` → `apps/web/src`

