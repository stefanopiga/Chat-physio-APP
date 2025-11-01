# Addendum: Strategia di Mocking per Autenticazione Supabase nei Test E2E

⚠️ **DEPRECATO** - Questo documento descrive il pattern legacy di mocking pre-refactoring.

**Status**: Deprecated  
**Priority**: Low  
**Date**: 2025-10-01  
**Scope**: Test End-to-End con Playwright per rotte protette da autenticazione  
**Sostituito da**: `addendum-auth-service-refactoring.md` (Sezione 5.2)

---

## ⚠️ Nota di Deprecazione

Questo documento descrive il pattern di mocking utilizzato **prima** del refactoring di `AuthService`.

**Pattern legacy** (descritto in questo documento):
- Doppia navigazione
- `page.evaluate()` e `waitForFunction()`
- Mock diretto di `window.supabase`
- ~50 righe di codice per test
- Fragile e lento

**Nuovo pattern** (post-refactoring):
- Navigazione singola
- `page.addInitScript()` con `__mockAuthService`
- Mock del servizio di astrazione
- ~20 righe di codice per test
- Robusto e veloce

**Per nuovi test**: Consultare `addendum-auth-service-refactoring.md` Sezione 5.2.

---

## 1. Contesto

I test E2E con Playwright per rotte protette da `AdminGuard` e `AuthGuard` richiedono la simulazione di una sessione utente autenticata. Il client Supabase nel browser verifica la sessione tramite:
- `supabase.auth.getSession()` - legge sessione da localStorage
- `supabase.auth.onAuthStateChange()` - monitora cambiamenti di stato

**Problema**: `AdminGuard` verifica `session?.user?.user_metadata?.role === "admin"` prima di rendere la pagina. Senza una sessione mockata valida, il guard redirige l'utente.

**Soluzione**: Utilizzare `page.addInitScript()` di Playwright per iniettare uno stato di sessione fittizio nel localStorage del browser PRIMA che il client Supabase venga inizializzato.

---

## 2. Strategia di Implementazione

### 2.1 Comprensione del Meccanismo

Supabase memorizza la sessione utente in `localStorage` con chiave:
```
sb-<project-ref>-auth-token
```

La struttura del dato è:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "expires_at": 1696176000,
  "refresh_token": "...",
  "user": {
    "id": "user-uuid",
    "email": "admin@example.com",
    "user_metadata": {
      "role": "admin"
    },
    ...
  }
}
```

### 2.2 Pattern di Mocking con Playwright

**Approccio raccomandato**: Iniettare session object completo nel localStorage usando `page.addInitScript()`.

**Vantaggi**:
- Nessuna chiamata API reale
- Controllo completo su payload e ruolo
- Riutilizzabile per diversi scenari (admin, student)
- Performance ottimale (no network latency)

---

## 3. Implementazione Completa

### 3.1 Helper Function Riutilizzabile

Creare file: `apps/web/tests/helpers/authMock.ts`

```typescript
import { Page } from "@playwright/test";

/**
 * Mock della sessione Supabase per test E2E.
 * 
 * Inietta uno stato di sessione fittizio nel localStorage del browser
 * PRIMA che la pagina venga caricata, permettendo ad AdminGuard e AuthGuard
 * di validare con successo l'autenticazione.
 * 
 * @param page - Istanza Page di Playwright
 * @param role - Ruolo utente da simulare ("admin" o "student")
 * @param userId - ID utente fittizio (opzionale)
 */
export async function mockSupabaseAuth(
  page: Page,
  role: "admin" | "student" = "admin",
  userId: string = "test-user-id"
): Promise<void> {
  // Recupera project ref da variabili ambiente (necessario per chiave localStorage)
  const supabaseUrl = process.env.VITE_SUPABASE_URL || "https://test.supabase.co";
  const projectRef = supabaseUrl.match(/https:\/\/([^.]+)\.supabase\.co/)?.[1] || "test";
  const storageKey = `sb-${projectRef}-auth-token`;

  // Costruisci session object fittizio
  const mockSession = {
    access_token: `mock-${role}-token-${Date.now()}`,
    token_type: "bearer",
    expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    refresh_token: `mock-refresh-token-${Date.now()}`,
    user: {
      id: userId,
      aud: "authenticated",
      role: "authenticated",
      email: `${role}@test.com`,
      email_confirmed_at: new Date().toISOString(),
      phone: "",
      confirmed_at: new Date().toISOString(),
      last_sign_in_at: new Date().toISOString(),
      app_metadata: {
        provider: "email",
        providers: ["email"],
      },
      user_metadata: {
        role: role, // CRITICO: questo campo è verificato da AdminGuard
      },
      identities: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  };

  // Inietta session nel localStorage PRIMA del caricamento della pagina
  await page.addInitScript(
    ({ key, session }) => {
      localStorage.setItem(key, JSON.stringify(session));
    },
    { key: storageKey, session: mockSession }
  );
}


/**
 * Rimuove lo stato di autenticazione mockato (cleanup tra test).
 */
export async function clearSupabaseAuth(page: Page): Promise<void> {
  await page.evaluate(() => {
    const keys = Object.keys(localStorage).filter(k => k.startsWith("sb-"));
    keys.forEach(key => localStorage.removeItem(key));
  });
}
```

### 3.2 Esempio di Utilizzo in Test (Story 4.1)

Aggiornare: `apps/web/tests/story-4.1.spec.ts`

```typescript
import { test, expect } from "@playwright/test";
import { mockSupabaseAuth, clearSupabaseAuth } from "./helpers/authMock";

test.describe("Story 4.1 - Admin Debug View", () => {
  
  test("admin autenticato naviga a /admin/debug e invia una query", async ({ page }) => {
    // ========== SETUP AUTH MOCK ==========
    // Inietta sessione admin PRIMA di navigare
    await mockSupabaseAuth(page, "admin");
    
    // ========== NAVIGAZIONE ==========
    await page.goto("/admin/debug");

    // Verifica che AdminGuard abbia concesso accesso
    await expect(
      page.getByRole("heading", { name: /Debug RAG/i })
    ).toBeVisible();

    // ========== INTERAZIONE UI ==========
    const textarea = page.locator("textarea#question");
    await textarea.fill("Esempio domanda di test");

    // Mock API backend response
    await page.route("**/api/v1/admin/debug/query", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          question: "Esempio domanda di test",
          answer: "Risposta di debug mockata",
          chunks: [
            {
              chunk_id: "chunk1",
              content: "Contenuto chunk 1",
              similarity_score: 0.95,
              metadata: {
                document_id: "doc1",
                document_name: "test.pdf",
                page_number: 1,
                chunking_strategy: "recursive",
              },
            },
          ],
          retrieval_time_ms: 100,
          generation_time_ms: 500,
        }),
      });
    });

    const submitButton = page.getByRole("button", { name: /Esegui Query Debug/i });
    await submitButton.click();

    // ========== ASSERTIONS ==========
    // Verifica rendering risposta
    await expect(
      page.getByRole("heading", { name: /Risposta Finale/i })
    ).toBeVisible();
    
    await expect(page.getByText("Risposta di debug mockata")).toBeVisible();
    
    // Verifica rendering chunks
    await expect(page.getByText("Chunk Recuperati (1)")).toBeVisible();
    await expect(page.getByText("Score: 0.950")).toBeVisible();
    
    // Verifica timing metrics
    await expect(page.getByText(/Retrieval: 100ms/)).toBeVisible();
    await expect(page.getByText(/Generation: 500ms/)).toBeVisible();
  });

  test("utente non autenticato viene rediretto da /admin/debug", async ({ page }) => {
    // NO auth mock - test redirect behavior
    await page.goto("/admin/debug");
    
    // Verifica redirect a home (comportamento di AdminGuard)
    await expect(page).toHaveURL("/");
  });

  test("utente student (non admin) viene rediretto da /admin/debug", async ({ page }) => {
    // Mock con ruolo student (non admin)
    await mockSupabaseAuth(page, "student");
    
    await page.goto("/admin/debug");
    
    // AdminGuard deve redirigere perché role !== "admin"
    await expect(page).toHaveURL("/");
  });

  // Cleanup dopo ogni test
  test.afterEach(async ({ page }) => {
    await clearSupabaseAuth(page);
  });
});
```

---

## 4. Pattern Avanzati

### 4.1 Mock con Token Scaduto

Per testare il comportamento di session expired:

```typescript
await page.addInitScript(({ key }) => {
  const expiredSession = {
    access_token: "expired-token",
    expires_at: Math.floor(Date.now() / 1000) - 3600, // 1 ora fa
    user: { /* ... */ }
  };
  localStorage.setItem(key, JSON.stringify(expiredSession));
}, { key: storageKey });
```

### 4.2 Intercettazione API Supabase (Alternativa)

Se necessario intercettare chiamate API reali:

```typescript
await page.route("**/auth/v1/user", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: "user-id",
      email: "admin@test.com",
      user_metadata: { role: "admin" }
    })
  });
});
```

**Nota**: Questo approccio è più fragile perché dipende dall'implementazione interna di Supabase.

---

## 5. Troubleshooting

### 5.1 AdminGuard continua a redirigere

**Causa**: Chiave localStorage errata o session object malformato.

**Debug**:
```typescript
await page.evaluate(() => {
  console.log("LocalStorage keys:", Object.keys(localStorage));
  const keys = Object.keys(localStorage).filter(k => k.startsWith("sb-"));
  keys.forEach(k => console.log(k, localStorage.getItem(k)));
});
```

**Fix**: Verificare che `projectRef` in `storageKey` corrisponda all'URL Supabase configurato.

### 5.2 Session non persiste tra navigazioni

**Causa**: `clearSupabaseAuth` chiamato troppo presto.

**Fix**: Chiamare cleanup solo in `afterEach`, non durante il test.

### 5.3 Token JWT richiesto dal backend

**Problema**: Backend valida signature JWT reale.

**Soluzione**: Mockare anche le risposte API backend con `page.route()` come mostrato negli esempi.

---

## 6. Best Practices

1. **Usa helper riutilizzabili**: Centralizzare logica di mocking in `authMock.ts`
2. **Cleanup consistente**: Sempre chiamare `clearSupabaseAuth` in `afterEach`
3. **Test isolati**: Ogni test deve settare il proprio stato auth
4. **Mock granulare**: Testare scenari diversi (admin, student, expired, no-auth)
5. **Non committare secrets**: Mai usare token reali nei test

---

## 7. Riferimenti

- **AdminGuard**: `apps/web/src/components/AdminGuard.tsx`
- **AuthGuard**: `apps/web/src/components/AuthGuard.tsx`
- **Supabase Client**: `apps/web/src/lib/supabaseClient.ts`
- **Playwright API**: https://playwright.dev/docs/api/class-page#page-add-init-script
- **Supabase Auth**: https://supabase.com/docs/guides/auth

---

## 8. Checklist di Validazione

Prima di considerare completa l'implementazione E2E:

- [ ] Helper `authMock.ts` creato con `mockSupabaseAuth` e `clearSupabaseAuth`
- [ ] Test admin happy path implementato e passante
- [ ] Test redirect per utente non autenticato
- [ ] Test redirect per utente non-admin (student)
- [ ] Cleanup `afterEach` implementato
- [ ] Tutti i test E2E passano (`pnpm test:e2e`)
- [ ] Task E2E marcato `[x]` in `docs/stories/4.1.admin-debug-view.md`

---

## 9. Note di Implementazione e Troubleshooting (Ottobre 2025)

### 9.1 Problemi Riscontrati Durante Implementazione Story 4.1

**Data**: 2025-10-01  
**Contesto**: Test E2E per `/admin/debug` con `AdminGuard` che verifica `user_metadata.role === "admin"`

#### Problema Principale: Mock Non Applicato

**Sintomo**:
- Test fallisce con `Error: expect(locator).toBeVisible() failed`
- Page snapshot mostra `AccessCodePage` invece di `AdminDebugPage`
- `AdminGuard` redirige a `/` perché non vede sessione admin

**Causa Root**:
Il client Supabase viene inizializzato PRIMA che gli script di mock possano intercettare i metodi `auth.getSession()` e `auth.onAuthStateChange()`. Le strategie tentate:

1. ❌ **page.route()** per HTTP - Supabase usa cache interno, non rilancia chiamate HTTP
2. ❌ **Object.defineProperty override** - Eseguito DOPO che `window.supabase` è già assegnato
3. ❌ **localStorage mock** - Supabase legge una sola volta all'init, chiave esatta sconosciuta

#### Soluzione Funzionante

Approccio **post-load injection** con doppia navigazione:

```ts
// 1. Setup route intercept (fallback)
await mockSupabaseAuth(page, "admin");

// 2. Prima navigazione - carica app
await page.goto("/admin/debug", { waitUntil: "domcontentloaded" });

// 3. Aspetta che window.supabase sia disponibile
await page.waitForFunction(() => (window as any).supabase != null, {
  timeout: 5000,
});

// 4. Inietta mock sui metodi auth
await page.evaluate(() => {
  const mockSession = { /* ... */ };
  const supabase = (window as any).supabase;
  if (supabase?.auth) {
    supabase.auth = {
      ...supabase.auth,
      getSession: async () => ({ data: { session: mockSession }, error: null }),
      onAuthStateChange: (callback) => {
        setTimeout(() => callback("SIGNED_IN", mockSession), 0);
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
    };
  }
});

// 5. Seconda navigazione - applica mock
await page.goto("/admin/debug", { waitUntil: "networkidle" });
```

**Perché funziona**:
- Prima navigazione: carica l'app e rende disponibile `window.supabase`
- `page.evaluate()`: mocka i metodi auth sul client già inizializzato
- Seconda navigazione: React re-esegue `AdminGuard` con metodi mockati

### 9.2 Prerequisito Fondamentale

**CRITICO**: `window.supabase` deve essere esposto per permettere il mocking.

In `apps/web/src/lib/supabaseClient.ts`:
```ts
export const supabase = createClient(supabaseUrl, supabaseAnonKey, options);

// Esponi su window per test E2E (solo in dev/test)
if (import.meta.env.DEV || import.meta.env.MODE === "test") {
  (window as any).supabase = supabase;
}
```

### 9.3 Best Practices Aggiornate

1. **Doppia navigazione è necessaria**: prima per setup, seconda per applicare mock
2. **`waitForFunction()` è affidabile**: garantisce che `window.supabase` esista
3. **`page.evaluate()` post-load**: unico modo per mockare client già inizializzato
4. **Cleanup robusto**: controllare `page.isClosed()` prima di `evaluate()` in `afterEach`

```ts
export async function clearSupabaseAuth(page: Page): Promise<void> {
  if (!page.isClosed()) {
    await page.evaluate(() => {
      const keys = Object.keys(localStorage).filter((k) => k.startsWith("sb-"));
      keys.forEach((key) => localStorage.removeItem(key));
    }).catch(() => {});
  }
}
```

5. **Error handling**: `.catch()` su `evaluate()` per evitare crash se pagina si chiude

### 9.4 Limitazioni Conosciute

- **Performance**: doppia navigazione rallenta i test (~2x tempo)
- **Timing fragile**: `setTimeout` a 0ms in `onAuthStateChange` può causare race conditions
- **Accoppiamento**: dipende da `window.supabase` esposto (non funziona in produzione)

### 9.5 Alternative Non Implementate

**Vite Plugin per Test**:
Potrebbe iniettare mock a build-time per ambiente test, evitando doppia navigazione. Richiede:
- Plugin Vite custom
- Configurazione `vitest` separata da Playwright
- Maggiore complessità setup

**Supabase Test Client**:
Libreria dedicata per mocking (non esiste ufficialmente). Richiederebbe sviluppo custom wrapper.

### 9.6 Raccomandazioni per il Team

1. **Standardizzare pattern**: usare `waitForFunction` + `evaluate` + doppia navigazione per tutti i test con guards
2. **Documentare timing**: annotare nei test quando è necessario `networkidle` vs `domcontentloaded`
3. **Refactoring futuro**: valutare estrazione logica auth in servizio mockabile senza dipendenza da Supabase client

---

**Status Post-Implementazione**: ✅ Implementato il 2025-10-01 con strategia post-load injection (waitForFunction + evaluate + doppia navigazione).

**Ultimo Aggiornamento**: 2025-10-01 - Documentate problematiche e soluzione finale per Story 4.1

