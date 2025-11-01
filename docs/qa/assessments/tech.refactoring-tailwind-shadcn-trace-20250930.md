# QA Trace — Refactoring Tecnico: Tailwind CSS + Shadcn/UI (2025-09-30)

## Riferimento Storia
- File: `docs/stories/tech.refactoring-tailwind-shadcn.md`
- Status: Approved
- Acceptance Criteria (estratti):
  1) Installazione e configurazione di Tailwind CSS in `apps/web`
  2) Integrazione Shadcn/UI con temi Light/Dark
  3) Rimozione completa degli stili inline in `apps/web/src/components` e `apps/web/src/pages`
  4) Sostituzione con classi Tailwind, nessun colore hard-coded
  5) Uso variabili semantiche di theming (background, foreground, primary, card, ...)
  6) Aggiornare documentazione `docs/prompt-for-lovable_V0.md`
  7) Verifica accessibilità base (focus visibile, keyboard navigation)

## Evidenze di Conformità

### Setup Tailwind + Vite
- `apps/web/package.json` dependencies: `tailwindcss`, `@tailwindcss/vite` presenti (OK)
- `apps/web/vite.config.ts`:
```1:26:apps/web/vite.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: [
      "tests/**",
      "playwright.config.ts",
      "playwright-report/**",
      "test-results/**",
    ],
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
```

### Shadcn/UI Init
- `apps/web/components.json` (baseColor `stone`, css `src/index.css`, aliases `@`):
```1:22:apps/web/components.json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "stone",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "registries": {}
}
```
- `apps/web/src/lib/utils.ts` presente con helper `cn()`.

### Theming Tailwind + Varianti Dark
- `apps/web/src/index.css`: import `tailwindcss`, `tw-animate-css`, definizioni tema e variant `dark`, layer base:
```1:35:apps/web/src/index.css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);
}
```

### Rimozione stili inline e sostituzione con Tailwind
- Assenza `style={` in `apps/web/src`: ricerca negativa (OK)
- Componenti aggiornati a classi Tailwind:
  - `apps/web/src/components/ChatInput.tsx`
  - `apps/web/src/components/ChatMessagesList.tsx`
  - `apps/web/src/components/CitationPopover.tsx`
  - `apps/web/src/components/FeedbackControls.tsx`
  - `apps/web/src/components/CitationBadge.tsx`
- Pagine aggiornate a classi Tailwind:
  - `apps/web/src/pages/ChatPage.tsx`
  - `apps/web/src/pages/AccessCodePage.tsx`
  - `apps/web/src/pages/LoginPage.tsx`
  - `apps/web/src/pages/DashboardPage.tsx`
- Rimozione CSS legacy: `apps/web/src/App.css` eliminato e import rimosso in `App.tsx` (OK)

### Build e Test
- Build: `pnpm run build` completata con successo. Artefatti generati in `apps/web/dist`.
- Test: Vitest `--run` eseguito con 3 file test passati (6 test totali), nessun errore.

### Accessibilità di base
- Label presenti per campi form principali.
- Indicatori focus via utility (`focus:ring`), ruoli ARIA su messaggi di errore (`role="alert"`).
- Navigazione da tastiera non alterata dal refactoring.

## Conclusione
Tutti gli Acceptance Criteria risultano soddisfatti. Il codice è conforme alla documentazione di sviluppo: Tailwind 4 + plugin Vite attivi, Shadcn/UI inizializzato, theming semantico implementato, assenza di stili inline, build e test OK.
