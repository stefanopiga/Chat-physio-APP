# NFR Assessment — Refactoring Tecnico: Tailwind CSS + Shadcn/UI (2025-09-30)

## Riferimento Storia
- File: `docs/stories/tech.refactoring-tailwind-shadcn.md`
- Status: Approved

## Ambiti NFR Valutati
- Maintainability (manutenibilità)
- Consistenza UI/UX
- Accessibilità (A11y)
- Performance build/runtime
- Portabilità/standardizzazione dello stack

## Evidenze

### Maintainability
- Eliminazione stili inline a favore di classi Tailwind: componenti e pagine migrati.
- Alias `@` per import coerenti:
```1:14:apps/web/vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
```
- Config centralizzata del tema in `src/index.css` con variabili semantiche, dark variant e layer base.

### Consistenza UI/UX
- BaseColor Shadcn `stone`, stile `new-york`, icone `lucide`:
```1:18:apps/web/components.json
{
  "tailwind": {
    "css": "src/index.css",
    "baseColor": "stone",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "ui": "@/components/ui"
  }
}
```
- Componenti interni allineati a token (`bg-card`, `text-card-foreground`, `border-border`).

### Accessibilità
- Focus visibile e outline globale:
```113:120:apps/web/src/index.css
@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```
- Errori annunciati con `role="alert"` (es. `AccessCodePage.tsx`, `LoginPage.tsx`).

### Performance build/runtime
- Plugin Vite ufficiale `@tailwindcss/vite` v4 integrato.
- Build riuscita: `pnpm run build` completata senza errori; bundle js/css generati.

### Portabilità/standardizzazione
- Stack documentato in `docs/architecture/addendum-tailwind-shadcn-setup.md` seguito (plugin, alias, import Tailwind v4).
- Dipendenze standard: `tailwindcss`, `@tailwindcss/vite`, `clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`.

## Rischi Residui e Mitigazioni
- Rischio: assenza di componenti Shadcn preconfezionati (solo utils/tema). Mitigazione: usare `shadcn add <component>` quando necessario per UI complessa.
- Rischio: regressioni visive non coperte da snapshot. Mitigazione: introdurre test visivi/Playwright aggiornati.

## Conclusione
NFR soddisfatti: manutenibilità migliorata, coerenza visiva stabilita tramite tema semantico, a11y base preservata, build performante e standard stack adottato. La storia risulta conforme ai requisiti non funzionali dichiarati.
