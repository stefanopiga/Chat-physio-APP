# Addendum — Setup Tailwind CSS e Shadcn/UI (Vite)

## Installazione di Tailwind CSS (per Vite)

### 1. Comandi da Terminale

```bash
pnpm add tailwindcss @tailwindcss/vite
```

### 2. Configurazione Plugin Vite

vite.config.ts

```typescript
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
  ],
})
```

### 3. Configurazione File CSS Principale

```css
@import "tailwindcss";
```

Nota: La documentazione ufficiale di Tailwind CSS per Vite (`https://tailwindcss.com/docs/installation`) non contiene istruzioni per la creazione di `tailwind.config.js` o per l'utilizzo delle direttive `@tailwind base`, `@tailwind components`, `@tailwind utilities`. Il metodo documentato utilizza il plugin `@tailwindcss/vite` e la direttiva `@import`.

---

## Installazione di Shadcn/UI (per Vite)

### 1. Comando di Inizializzazione

```bash
pnpm dlx shadcn@latest init
```

### 2. Opzioni di Configurazione Principali

* Scelta del colore base (esempio: `Which color would you like to use as base color? › Neutral`)

Configurazioni preliminari richieste (prima del comando init):

* Installazione dipendenze Tailwind:
```bash
pnpm add tailwindcss @tailwindcss/vite
```

* Configurazione tsconfig.json con baseUrl e paths:
```json
"compilerOptions": {
  "baseUrl": ".",
  "paths": {
    "@/*": ["./src/*"]
  }
}
```

* Configurazione vite.config.ts con risoluzione alias:
```bash
pnpm add -D @types/node
```

```typescript
import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
```
