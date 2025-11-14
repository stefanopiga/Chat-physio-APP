# Vite Environment Variables

## Variabili Built-in

Disponibili sempre via `import.meta.env`:

```typescript
import.meta.env.MODE          // "development" | "production" | custom
import.meta.env.BASE_URL      // Base URL (da config base)
import.meta.env.PROD          // boolean - se produzione
import.meta.env.DEV           // boolean - se development
import.meta.env.SSR           // boolean - se server-side rendering
```

---

## Variabili Custom

**Requisito:** Prefix `VITE_` per esposizione a client.

**File .env:**
```bash
VITE_API_URL=https://api.example.com
VITE_APP_TITLE=My App
DB_PASSWORD=secret123  # NON esposta (no VITE_ prefix)
```

**Uso in codice:**
```typescript
console.log(import.meta.env.VITE_API_URL)      // "https://api.example.com"
console.log(import.meta.env.VITE_APP_TITLE)    // "My App"
console.log(import.meta.env.DB_PASSWORD)       // undefined
```

**Nota:** Tutte le variabili sono stringhe. Converti al tipo necessario:
```typescript
const maxRetries = Number(import.meta.env.VITE_MAX_RETRIES)
const featureEnabled = import.meta.env.VITE_FEATURE === 'true'
```

---

## File .env

**Gerarchia caricamento:**
```
.env                  # Caricato sempre
.env.local            # Caricato sempre, ignorato da git
.env.[mode]           # Solo per mode specifico
.env.[mode].local     # Solo per mode specifico, ignorato da git
```

**Priorità (dal più alto al più basso):**
1. Variabili ambiente esistenti (es. `VITE_KEY=123 vite build`)
2. `.env.[mode].local`
3. `.env.[mode]`
4. `.env.local`
5. `.env`

**Esempio struttura:**
```
.env                    # Defaults condivisi
.env.local              # Override locali (non committare)
.env.development        # Development mode
.env.production         # Production mode
.env.staging            # Staging mode (custom)
```

---

## Variable Expansion

**Sintassi dotenv-expand:**
```bash
KEY=123
NEW_KEY1=test$foo        # test
NEW_KEY2=test\$foo       # test$foo
NEW_KEY3=test$KEY        # test123
```

**Escape $ con backslash:**
```bash
VITE_PRICE=\$19.99       # $19.99
```

---

## TypeScript IntelliSense

**File `src/vite-env.d.ts`:**
```typescript
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_APP_TITLE: string
  readonly VITE_MAX_RETRIES: string
  readonly VITE_FEATURE_FLAG: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

**Strict mode (disallow unknown keys):**
```typescript
interface ViteTypeOptions {
  strictImportMetaEnv: unknown
}

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  // Qualsiasi altra key causerà errore TS
}
```

**Importante:** Non importare nulla in `vite-env.d.ts` o romperà l'augmentation.

---

## HTML Replacement

**Sintassi `%VAR_NAME%`:**
```html
<h1>Running in %MODE%</h1>
<p>API: %VITE_API_URL%</p>
```

**Rendering:**
```html
<h1>Running in production</h1>
<p>API: https://api.example.com</p>
```

**Nota:** Variabili non esistenti non vengono sostituite (rimane `%NON_EXISTENT%`).

---

## Modes

**Default modes:**
- `vite` (dev server) → mode = "development"
- `vite build` → mode = "production"

**Custom mode con --mode:**
```bash
vite build --mode staging
```

**File .env.staging:**
```bash
VITE_API_URL=https://staging-api.example.com
VITE_APP_TITLE=My App (staging)
```

---

## NODE_ENV vs Mode

**Sono concetti diversi:**

| Command | NODE_ENV | Mode | import.meta.env.PROD | import.meta.env.DEV |
|---------|----------|------|---------------------|---------------------|
| vite build | production | production | true | false |
| vite build --mode development | production | development | true | false |
| NODE_ENV=development vite build | development | production | false | true |
| NODE_ENV=development vite build --mode dev | development | development | false | true |

**Best practice:**
- Usa `--mode` per environment-specific configs
- Lascia `NODE_ENV` al default (gestito da Vite)
- `import.meta.env.MODE` per logica condizionale env

**Impostare NODE_ENV in .env:**
```bash
# .env.testing
NODE_ENV=development  # Forza development build per testing
```

---

## Security Best Practices

**Gitignore:**
```gitignore
# Local env files
.env.local
.env.*.local
```

**Non esporre secrets:**
```bash
# ❌ MAI fare questo
VITE_API_SECRET=super_secret_key_123

# ✓ Secrets solo server-side
API_SECRET=super_secret_key_123  # No VITE_ prefix
```

**Nota critica:** Qualsiasi `VITE_*` var finisce nel bundle client. Non includere:
- API keys private
- Database credentials
- Encryption keys
- Access tokens

---

## Custom Prefix

**Config vite.config.ts:**
```typescript
export default defineConfig({
  envPrefix: 'APP_',  // Default: 'VITE_'
})
```

**File .env:**
```bash
APP_API_URL=https://api.example.com
```

---

## Runtime Config (Alternative)

**Per config che cambiano senza rebuild:**

**public/config.js:**
```javascript
window.APP_CONFIG = {
  API_URL: 'https://api.example.com',
  FEATURE_FLAGS: {
    newFeature: true,
  },
}
```

**index.html:**
```html
<script src="/config.js"></script>
```

**Uso:**
```typescript
const apiUrl = (window as any).APP_CONFIG.API_URL
```

---

## Testing

**Vitest setup:**
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    env: {
      VITE_API_URL: 'http://localhost:3000',
    },
  },
})
```

**Override in test:**
```typescript
import { vi } from 'vitest'

vi.stubEnv('VITE_API_URL', 'http://mock-api.test')
```

---

## Bun Compatibility

**Issue:** Bun auto-carica `.env` in `process.env` prima di Vite.

**Workaround:** Configurare Bun per non caricare automaticamente o usare Vite's env handling esclusivamente.

**Reference:** https://github.com/oven-sh/bun/issues/5515

---

## Repository

https://vitejs.dev/guide/env-and-mode.html
