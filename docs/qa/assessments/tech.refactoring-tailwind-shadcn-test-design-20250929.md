# Test Design — Refactoring Tecnico: Tailwind CSS e Shadcn/UI

## Riferimenti
- Fonte primaria: `docs/stories/tech.refactoring-tailwind-shadcn.md`
- Requisiti accessibilità: `docs/front-end-spec.md` Sez. 7 L227–L243
- Vincoli UI/Dev: `docs/prompt-for-lovable_V0.md` Sez. 3 (L50–L55, L59)

## Gating / Prerequisiti (Bloccanti)
- Tailwind CSS installato e configurato nel progetto `apps/web` (build OK, classi applicabili).
- Shadcn/UI integrato, con theming Light/Dark disponibile e variabili semantiche attive.
- Rimozione completa degli stili inline dai componenti `apps/web/src/components` e `apps/web/src/pages`.
- Aggiornamento documentazione `docs/prompt-for-lovable_V0.md` con clausola di conformità.
 - Configurazione plugin Vite Tailwind presente. [Fonte: `docs/architecture/addendum-tailwind-shadcn-setup.md` L15–L23]
 - CSS principale include `@import "tailwindcss";`. [Fonte: `docs/architecture/addendum-tailwind-shadcn-setup.md` L26–L31]
 - Alias vite/tsconfig configurati per Shadcn prima dell'init. [Fonte: `docs/architecture/addendum-tailwind-shadcn-setup.md` L55–L83]

## Obiettivi di Test
- Verificare l’installazione/configurazione di Tailwind (classi applicate con effetto visibile, build senza errori).
- Verificare l’integrazione Shadcn/UI (render componenti base, theming funzionante, nessun colore hard-coded).
- Verificare la rimozione degli stili inline e l’uso di classi utility Tailwind.
- Verificare la presenza di variabili semantiche di theming su componenti UI rilevanti.
- Verificare accessibilità di base: focus visibile e tab order invariato.

## Strategia di Testing
- Static code search per tracciare `style={` e valori di colore esadecimali/letterali.
- Smoke test di build (`pnpm --filter web build`) e preview manuale.
- Snapshot visuali su key views (Login, Chat, Admin) prima/dopo refactor.
- Interazione manuale con componenti Shadcn/UI introdotti.
 - Verifica `vite.config.ts` per presenza plugin `@tailwindcss/vite` e alias `@`. [Fonte: addendum]

## Casi di Test

### TD-001 — Tailwind installazione/configurazione
- Step: Verificare plugin `@tailwindcss/vite` in `vite.config.ts` e `@import "tailwindcss";` nel CSS principale.
- Expect: Build OK; classi Tailwind (es. `bg-background`, `text-foreground`, `p-4`) hanno effetto.

### TD-002 — Shadcn/UI integrazione e theming
- Step: Render minimo `Button`, `Card`, `Popover` con tokens semantici.
- Expect: Theming Light/Dark funziona senza hard-coded colors; nessun warning accessibilità.
 - Note: Verificare alias vite/tsconfig (`@` → `./src/*`).

### TD-003 — Rimozione stili inline
- Step: Ricerca `style={` in `apps/web/src/components` e `apps/web/src/pages`.
- Expect: 0 occorrenze residue.

### TD-004 — Variabili semantiche
- Step: Verifica classi Tailwind mappate a tokens (es. `bg-background`, `text-foreground`, `border-border`, `bg-card`).
- Expect: Componenti chiave usano esclusivamente tokens semantici.

### TD-005 — Accessibilità di base
- Step: Navigazione tastiera su componenti refactorizzati, focus ring visibile.
- Expect: Nessuna regressione nel tab order; indicatori di focus coerenti.

## Metriche
- non disponibile nella fonte
