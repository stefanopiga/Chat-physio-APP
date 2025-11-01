# Test Design — Tech Debt: Refactoring del Servizio di Autenticazione

## Riferimenti

- **Fonte primaria**: `docs/stories/tech-debt-auth-service-refactoring.md`
- **Addendum tecnico**: `docs/architecture/addendum-auth-service-refactoring.md`
- **Profilo rischi**: `docs/qa/assessments/tech-debt-auth-refactoring-risk-20251001.md`
- **Problema originale**: `docs/qa/assessments/4.1-team-discussion-points-20251001.md`

---

## Gating / Prerequisiti (Bloccanti)

### Dipendenze Tecniche (Pre-Refactoring)

- [ ] **Story 4.1 completata e in produzione**: Pattern corrente con doppia navigazione stabilizzato. [Fonte: `tech-debt-auth-service-refactoring.md` L214]
- [ ] **Baseline Performance documentata**: Tempo esecuzione suite E2E attuale misurato (riferimento per target -40%). [Fonte: `tech-debt-auth-service-refactoring.md` L78-80]
- [ ] **Baseline Coverage documentata**: Coverage frontend >= 80% come riferimento. [Fonte: `tech-debt-auth-service-refactoring.md` L93]
- [ ] **Test E2E esistenti passanti**: Story 1.2, 1.3, 3.3, 4.1 al 100% green. [Fonte: `tech-debt-auth-service-refactoring.md` L91]

### Prerequisiti Implementativi (Pre-Testing)

- [ ] **AuthService creato**: File `apps/web/src/services/authService.ts` implementato con interfaccia `IAuthService`. [Fonte: `tech-debt-auth-service-refactoring.md` L49-54, L110]
- [ ] **Componenti migrati**: `AdminGuard.tsx` e `AuthGuard.tsx` usano `authService` invece di `supabase` diretto. [Fonte: `tech-debt-auth-service-refactoring.md` L56-59]
- [ ] **Import verificati**: Nessun componente importa `supabase` da `supabaseClient.ts` (verificato con script CI). [Fonte: `tech-debt-auth-service-refactoring.md` L59, L267-269]
- [ ] **window.supabase rimosso**: Exposure in `supabaseClient.ts` eliminato. [Fonte: `tech-debt-auth-service-refactoring.md` L61, L137]

### Environment Setup

- [ ] **Vitest configurato**: Mock setup per `vi.mock` funzionante
- [ ] **Playwright aggiornato**: `addInitScript` compatibile con nuovo pattern
- [ ] **React Testing Library**: Disponibile per unit test componenti
- [ ] **Coverage tools**: Istanbul/nyc configurati per report cumulativo

---

## Obiettivi di Test

### Obiettivi Primari
1. **Regressione Zero**: Tutti i flussi di autenticazione (admin, student) funzionano identicamente a pre-refactoring
2. **Coverage Target**: authService >= 85%, AdminGuard >= 90%, AuthGuard >= 90%
3. **Performance Target**: Test E2E -40% tempo esecuzione (accettabile: >= -30%)
4. **Stabilità Target**: Zero flaky test su 10 run consecutivi

### Obiettivi Secondari
5. **Mocking Semplificato**: Test E2E ridotti da ~50 a ~15 righe di codice
6. **Testabilità Migliorata**: Nessun `page.evaluate()`, `waitForFunction()`, doppia navigazione
7. **Architettura Validata**: Dependency Inversion applicato correttamente

---

## Casi di Test — Unit Test

### UT-AUTH — AuthService (apps/web/src/services/authService.ts)

**UT-AUTH-001** — `getSession()` ritorna sessione da Supabase client
- **Given**: Supabase client mockato con sessione admin
- **When**: `authService.getSession()` chiamato
- **Then**: Ritorna `{ data: { session: mockSession }, error: null }`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-002** — `getSession()` gestisce errore Supabase
- **Given**: Supabase client mockato con errore
- **When**: `authService.getSession()` chiamato
- **Then**: Ritorna `{ data: { session: null }, error: mockError }`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-003** — `onAuthStateChange()` registra callback
- **Given**: Callback mock fornito
- **When**: `authService.onAuthStateChange(callback)` chiamato
- **Then**: Callback invocato con evento `SIGNED_IN` e sessione; subscription ritornata
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-004** — `isAdmin()` verifica role=admin
- **Given**: Session con `user_metadata.role = "admin"`
- **When**: `authService.isAdmin(session)` chiamato
- **Then**: Ritorna `true`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-005** — `isAdmin()` falso per session null
- **Given**: Session = null
- **When**: `authService.isAdmin(null)` chiamato
- **Then**: Ritorna `false`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-006** — `isAdmin()` falso per role diverso
- **Given**: Session con `user_metadata.role = "student"`
- **When**: `authService.isAdmin(session)` chiamato
- **Then**: Ritorna `false`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-007** — `isStudent()` verifica role=student
- **Given**: Session con `user_metadata.role = "student"`
- **When**: `authService.isStudent(session)` chiamato
- **Then**: Ritorna `true`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-008** — `isAuthenticated()` verifica sessione non null
- **Given**: Session valida
- **When**: `authService.isAuthenticated(session)` chiamato
- **Then**: Ritorna `true`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-009** — `isAuthenticated()` falso per null
- **Given**: Session = null
- **When**: `authService.isAuthenticated(null)` chiamato
- **Then**: Ritorna `false`
- **Fonte**: `addendum-auth-service-refactoring.md` L49-73

**UT-AUTH-010** — Edge case: session malformata senza user_metadata
- **Given**: Session = `{ user: {} }` (senza user_metadata)
- **When**: `authService.isAdmin(session)` chiamato
- **Then**: Ritorna `false` senza crash
- **Mitigazione**: Risk R-AUTH-5 (interfaccia stabile)

**Coverage Target UT-AUTH**: >= 85%

---

### UT-GUARD — AdminGuard Component

**UT-GUARD-001** — Renderizza children quando admin autenticato
- **Given**: `authService.getSession()` mockato con session admin; `authService.isAdmin()` ritorna `true`
- **When**: `<AdminGuard><div>Protected</div></AdminGuard>` renderizzato
- **Then**: "Protected" visibile nel DOM
- **Fonte**: `addendum-auth-service-refactoring.md` L195-228

**UT-GUARD-002** — Mostra loading mentre verifica sessione
- **Given**: `authService.getSession()` promise pending
- **When**: `<AdminGuard>` renderizzato
- **Then**: "Verifica autorizzazione amministratore..." visibile
- **Fonte**: `addendum-auth-service-refactoring.md` L105-153

**UT-GUARD-003** — Redirige a "/" quando session null
- **Given**: `authService.getSession()` ritorna `{ data: { session: null } }`
- **When**: `<AdminGuard>` renderizzato
- **Then**: `navigate("/")` chiamato
- **Fonte**: `addendum-auth-service-refactoring.md` L105-153

**UT-GUARD-004** — Redirige quando role != admin
- **Given**: `authService.getSession()` ritorna session student; `authService.isAdmin()` ritorna `false`
- **When**: `<AdminGuard>` renderizzato
- **Then**: `navigate("/")` chiamato
- **Fonte**: `addendum-auth-service-refactoring.md` L105-153

**UT-GUARD-005** — Cleanup subscription su unmount
- **Given**: Component montato con subscription attiva
- **When**: Component smontato (unmount)
- **Then**: `subscription.unsubscribe()` chiamato
- **Mitigazione**: Risk R-AUTH-6 (memory leak)

**UT-GUARD-006** — onAuthStateChange aggiorna sessione
- **Given**: Component montato; `onAuthStateChange` callback registrato
- **When**: Callback invocato con nuova sessione
- **Then**: Stato `session` aggiornato; re-render triggrato
- **Fonte**: `addendum-auth-service-refactoring.md` L105-153

**Coverage Target UT-GUARD**: >= 90%

---

### UT-AUTH-GUARD — AuthGuard Component

**UT-AUTH-GUARD-001** — Renderizza children quando autenticato
- **Given**: `authService.getSession()` ritorna session valida; `authService.isAuthenticated()` ritorna `true`
- **When**: `<AuthGuard><div>Chat</div></AuthGuard>` renderizzato
- **Then**: "Chat" visibile
- **Fonte**: `addendum-auth-service-refactoring.md` L233-263

**UT-AUTH-GUARD-002** — Redirige quando non autenticato
- **Given**: `authService.getSession()` ritorna `null`; `authService.isAuthenticated()` ritorna `false`
- **When**: `<AuthGuard>` renderizzato
- **Then**: `navigate("/")` chiamato
- **Fonte**: `addendum-auth-service-refactoring.md` L233-263

**UT-AUTH-GUARD-003** — Mostra loading durante verifica
- **Given**: `authService.getSession()` promise pending
- **When**: `<AuthGuard>` renderizzato
- **Then**: "Verifica autenticazione..." visibile
- **Fonte**: `addendum-auth-service-refactoring.md` L233-263

**Coverage Target UT-AUTH-GUARD**: >= 90%

---

## Casi di Test — Integration Test

### IT-AUTH — AuthService Integration

**IT-AUTH-001** — AuthService integrato con Supabase client reale (dev mode)
- **Given**: Supabase client configurato in dev environment
- **When**: `authService.getSession()` chiamato senza mock
- **Then**: Chiamata propagata a `supabase.auth.getSession()` reale
- **Note**: Test opzionale, richiede Supabase dev instance

**IT-AUTH-002** — Singleton instance condiviso tra componenti
- **Given**: Due componenti importano `authService`
- **When**: Modifiche a `authService` in componente A
- **Then**: Modifiche visibili in componente B (stessa istanza)
- **Fonte**: `addendum-auth-service-refactoring.md` L73

---

## Casi di Test — E2E (Playwright)

### E2E-4.1 — Admin Debug View (Story 4.1 Migrata)

**E2E-4.1-001** — Admin autenticato accede /admin/debug (nuovo pattern)
- **Given**: Mock `authService` con session admin tramite `addInitScript`
- **When**: Navigazione singola a `/admin/debug`
- **Then**: Heading "Debug RAG" visibile senza doppia navigazione
- **Fonte**: `tech-debt-auth-service-refactoring.md` L65-69, L229-244
- **Mitigazione**: Risk R-AUTH-4 (flaky test)

**E2E-4.1-002** — Non autenticato rediretto da /admin/debug
- **Given**: Nessun mock auth (session null)
- **When**: Navigazione a `/admin/debug`
- **Then**: Redirect a "/" (comportamento AdminGuard)
- **Fonte**: `tech-debt-auth-service-refactoring.md` L65-69

**E2E-4.1-003** — Student (non admin) rediretto da /admin/debug
- **Given**: Mock `authService` con session student
- **When**: Navigazione a `/admin/debug`
- **Then**: Redirect a "/"
- **Fonte**: `tech-debt-auth-service-refactoring.md` L65-69

**E2E-4.1-004** — Query debug completa (happy path)
- **Given**: Mock admin auth + mock backend response
- **When**: Submit query "test domanda"
- **Then**: Risposta e chunk visualizzati; timing metrics presenti
- **Fonte**: `tech-debt-auth-service-refactoring.md` L65-69

---

### E2E-1.2 — Admin Login (Regression)

**E2E-1.2-001** — Login admin funzionale dopo refactoring
- **Given**: Credenziali admin valide
- **When**: Login flow completato
- **Then**: Redirect a dashboard admin; sessione attiva
- **Fonte**: `tech-debt-auth-service-refactoring.md` L84-89
- **Mitigazione**: Risk R-AUTH-1 (regressione autenticazione)

---

### E2E-1.3 — Student Access Code (Regression)

**E2E-1.3-001** — Access code validation funzionale
- **Given**: Access code valido
- **When**: Student inserisce codice
- **Then**: Accesso concesso; sessione student attiva
- **Fonte**: `tech-debt-auth-service-refactoring.md` L84-89
- **Mitigazione**: Risk R-AUTH-1 (regressione autenticazione)

---

### E2E-3.3 — Student Chat (Regression)

**E2E-3.3-001** — Chat protetta accessibile a studenti autenticati
- **Given**: Mock student auth
- **When**: Navigazione a `/chat` (o rotta chat)
- **Then**: Chat UI visibile; query funzionante
- **Fonte**: `tech-debt-auth-service-refactoring.md` L84-89
- **Mitigazione**: Risk R-AUTH-1 (regressione autenticazione)

**E2E-3.3-002** — Chat bloccata per non autenticati
- **Given**: Nessun auth mock
- **When**: Navigazione a `/chat`
- **Then**: Redirect a "/" (comportamento AuthGuard)
- **Fonte**: `tech-debt-auth-service-refactoring.md` L84-89

---

### E2E-PERF — Performance Test

**E2E-PERF-001** — Tempo esecuzione suite E2E ridotto
- **Given**: Baseline tempo esecuzione pre-refactoring documentato
- **When**: Suite E2E completa eseguita con nuovo pattern
- **Then**: Tempo totale ridotto >= 40% (accettabile: >= 30%)
- **Fonte**: `tech-debt-auth-service-refactoring.md` L78-80, L199
- **Mitigazione**: Risk R-AUTH-3 (performance degradation)

**E2E-PERF-002** — Nessuna doppia navigazione nei test
- **Given**: Test E2E analizzati per pattern
- **When**: Code review test files
- **Then**: Zero occorrenze di doppia `page.goto()` per stesso URL
- **Fonte**: `tech-debt-auth-service-refactoring.md` L65-69

---

### E2E-STABILITY — Stability Test

**E2E-STABILITY-001** — Zero flaky test su 10 run consecutivi
- **Given**: Suite E2E completa
- **When**: Eseguita 10 volte consecutive senza modifiche
- **Then**: 100% green su tutti i 10 run
- **Fonte**: `tech-debt-auth-service-refactoring.md` L80, L207
- **Mitigazione**: Risk R-AUTH-4 (flaky test)

---

## Casi di Test — Sicurezza

### SEC-AUTH — Security Validation

**SEC-AUTH-001** — isAdmin() non bypassabile con session crafted
- **Given**: Session object con `user_metadata.role = "hacker"`
- **When**: `authService.isAdmin(session)` chiamato
- **Then**: Ritorna `false`
- **Mitigazione**: Risk R-AUTH-1 (security regression)

**SEC-AUTH-002** — Session validation robusta contro injection
- **Given**: Session object malformata con prototype pollution
- **When**: `authService.isAdmin()` chiamato
- **Then**: Nessun crash; ritorna `false`
- **Mitigazione**: Risk R-AUTH-5 (interface stability)

---

## Casi di Test — Architettura

### ARCH-001 — Nessun import diretto supabase in componenti
- **Given**: Script CI `pnpm run check:auth-imports`
- **When**: Eseguito su `apps/web/src/components/`
- **Then**: Zero match per pattern `import.*supabase.*from.*supabaseClient`
- **Fonte**: `tech-debt-auth-service-refactoring.md` L59, L267-269
- **Mitigazione**: Risk R-AUTH-2 (incompletezza migrazione)

**ARCH-002** — window.supabase non esposto
- **Given**: Build produzione
- **When**: Inspect `supabaseClient.ts` compiled code
- **Then**: `window.supabase` assegnazione assente
- **Fonte**: `tech-debt-auth-service-refactoring.md` L61, L137

**ARCH-003** — Dependency Inversion applicato
- **Given**: Dependency graph analizzato
- **When**: Componenti verificati
- **Then**: AdminGuard/AuthGuard dipendono da `IAuthService` (interfaccia), non da Supabase client
- **Fonte**: `tech-debt-auth-service-refactoring.md` L206

---

## Backend Test Design

**Non Applicabile**: Questo refactoring riguarda solo frontend (React components + test E2E). Nessuna modifica al backend API.

---

## Test Strategy — Phased Approach

### Fase 1: Unit Test (Giorno 1)
1. Implementare UT-AUTH-001 → UT-AUTH-010 (authService)
2. Validare coverage authService >= 85%
3. Fix eventuali edge case scoperti

### Fase 2: Component Unit Test (Giorno 2)
4. Implementare UT-GUARD-001 → UT-GUARD-006 (AdminGuard)
5. Implementare UT-AUTH-GUARD-001 → UT-AUTH-GUARD-003 (AuthGuard)
6. Validare coverage componenti >= 90%

### Fase 3: E2E Regression (Giorno 3)
7. Migrare E2E-4.1-001 → E2E-4.1-004 (Story 4.1)
8. Migrare E2E-1.2-001 (Admin Login)
9. Migrare E2E-1.3-001 (Student Access Code)
10. Migrare E2E-3.3-001 → E2E-3.3-002 (Chat)

### Fase 4: Performance & Stability (Giorno 4)
11. Eseguire E2E-PERF-001 → E2E-PERF-002
12. Eseguire E2E-STABILITY-001 (10 run consecutivi)
13. Documentare metriche vs baseline

### Fase 5: Security & Architecture (Giorno 5)
14. Eseguire SEC-AUTH-001 → SEC-AUTH-002
15. Eseguire ARCH-001 → ARCH-003
16. Validazione finale pre-merge

---

## Metriche Minime (Gate Qualità)

### Coverage
- [ ] **authService**: >= 85% line coverage
- [ ] **AdminGuard**: >= 90% line coverage
- [ ] **AuthGuard**: >= 90% line coverage
- [ ] **Frontend totale**: >= 80% (mantenuto o migliorato)
- **Fonte**: `tech-debt-auth-service-refactoring.md` L73-77, L197-198

### Performance
- [ ] **Test E2E**: tempo totale ridotto >= 40% (accettabile: >= 30%)
- [ ] **Baseline documentata**: tempo pre-refactoring registrato per confronto
- **Fonte**: `tech-debt-auth-service-refactoring.md` L78-80, L199

### Stabilità
- [ ] **Zero flaky test**: 10 run consecutivi al 100% green
- [ ] **Nessun timeout**: tutti i test completano entro limiti configurati
- **Fonte**: `tech-debt-auth-service-refactoring.md` L80, L207

### Regressione
- [ ] **Tutti i test esistenti passano**: Story 1.2, 1.3, 3.3, 4.1 al 100%
- [ ] **Nessun breaking change**: flussi auth identici a pre-refactoring
- **Fonte**: `tech-debt-auth-service-refactoring.md` L84-89, L91

### Architettura
- [ ] **Zero import diretto supabase**: script CI passa senza errori
- [ ] **ESLint clean**: nessun warning su `no-restricted-imports`
- **Fonte**: `tech-debt-auth-service-refactoring.md` L59, L267-269

---

## Test Automation

### CI/CD Pipeline Integration

**Pre-Merge Checks** (Blocca merge se FAIL):
```yaml
# .github/workflows/auth-refactoring-validation.yml
- name: Verify No Direct Supabase Imports
  run: pnpm run check:auth-imports
  
- name: Unit Test AuthService
  run: pnpm test authService.test.ts --coverage
  
- name: Unit Test Guards
  run: pnpm test AdminGuard.test.tsx AuthGuard.test.tsx --coverage
  
- name: E2E Regression Suite
  run: pnpm test:e2e --grep "story-(1.2|1.3|3.3|4.1)"
  
- name: Coverage Gate
  run: pnpm run coverage:check --threshold=80
```

**Post-Merge Monitoring**:
- Smoke test automatici ogni 15min per prime 24h
- Alert se error rate auth > 5%

---

## Rollback Testing

### RT-001 — Rollback funzionale in < 15 minuti
- **Given**: Refactoring deployato in staging
- **When**: Procedura rollback eseguita (git revert + rebuild)
- **Then**: Versione precedente ripristinata; smoke test passano
- **Fonte**: Risk profile rollback strategy

---

## Test Data & Fixtures

### Mock Sessions
```typescript
// Fixtures per test
export const mockAdminSession = {
  user: {
    id: "admin-test-id",
    email: "admin@test.com",
    user_metadata: { role: "admin" }
  }
};

export const mockStudentSession = {
  user: {
    id: "student-test-id", 
    email: "student@test.com",
    user_metadata: { role: "student" }
  }
};

export const mockExpiredSession = {
  user: { /* ... */ },
  expires_at: Date.now() - 3600000 // 1 ora fa
};
```

---

## Traceability Matrix

| AC | Test Cases | Coverage |
|----|------------|----------|
| AC1: AuthService creato | UT-AUTH-001 → UT-AUTH-010 | Unit |
| AC2: Componenti migrati | UT-GUARD-001 → UT-GUARD-006, UT-AUTH-GUARD-001 → 003 | Unit |
| AC3: window.supabase rimosso | ARCH-002 | Architecture |
| AC4: Test E2E semplificati | E2E-4.1-001 → 004 | E2E |
| AC5: Mock standard | E2E-4.1-001, E2E-3.3-001 | E2E |
| AC6: Unit test creati | UT-GUARD-001 → 006, UT-AUTH-GUARD-001 → 003 | Unit |
| AC7: Performance migliorata | E2E-PERF-001 → 002 | E2E Performance |
| AC8: Nessuna regressione | E2E-1.2-001, E2E-1.3-001, E2E-3.3-001 → 002 | E2E Regression |
| AC9: Tutti test passano | E2E-STABILITY-001 | E2E Stability |
| AC10: Coverage >= 80% | Coverage metrics gate | CI/CD |

---

## Risk Mitigation Mapping

| Risk ID | Test Cases | Status |
|---------|------------|--------|
| R-AUTH-1 (Regressione) | E2E-1.2-001, E2E-1.3-001, E2E-3.3-001, E2E-4.1-001 | Covered |
| R-AUTH-2 (Migrazione incompleta) | ARCH-001 | Covered |
| R-AUTH-3 (Performance) | E2E-PERF-001 → 002 | Covered |
| R-AUTH-4 (Flaky test) | E2E-STABILITY-001 | Covered |
| R-AUTH-5 (Breaking interface) | UT-AUTH-010, SEC-AUTH-002 | Covered |
| R-AUTH-6 (Memory leak) | UT-GUARD-005 | Covered |

---

## Execution Schedule

| Giorno | Fase | Test Cases | Effort |
|--------|------|------------|--------|
| 1 | Unit authService | UT-AUTH-001 → 010 | 4h |
| 2 | Unit Guards | UT-GUARD-001 → 006, UT-AUTH-GUARD-001 → 003 | 4h |
| 3 | E2E Regression | E2E-4.1-001 → 004, E2E-1.2-001, E2E-1.3-001, E2E-3.3-001 → 002 | 6h |
| 4 | Performance | E2E-PERF-001 → 002, E2E-STABILITY-001 | 4h |
| 5 | Security + Arch | SEC-AUTH-001 → 002, ARCH-001 → 003, RT-001 | 3h |
| **TOTALE** | | **68 test cases** | **21h** |

---

## Note Implementative

### Pattern Mock Consigliato (E2E)

```typescript
// apps/web/tests/story-4.1.spec.ts (versione refactored)
import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).__mockAuthSession = {
      user: { user_metadata: { role: "admin" } }
    };
  });
});

test("admin accede a debug view", async ({ page }) => {
  await page.goto("/admin/debug"); // Navigazione singola
  await expect(page.getByRole("heading", { name: /Debug RAG/i })).toBeVisible();
});
```

### Pattern Mock Consigliato (Unit)

```typescript
// apps/web/src/components/__tests__/AdminGuard.test.tsx
import { vi } from "vitest";
import { authService } from "@/services/authService";

vi.mock("@/services/authService", () => ({
  authService: {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    isAdmin: vi.fn(),
  },
}));

it("renders children when admin", async () => {
  vi.mocked(authService.isAdmin).mockReturnValue(true);
  // ... test logic
});
```

---

## Sign-Off Checklist

Prima di considerare test design completo:

- [ ] Tutti gli AC coperti da almeno un test case
- [ ] Tutti i rischi critici/high hanno test di mitigazione
- [ ] Metriche minime definite e misurabili
- [ ] Traceability matrix completa
- [ ] CI/CD integration specificata
- [ ] Rollback testing incluso

---

**Status**: ✅ Test Design Completo  
**Prepared by**: QA Team  
**Review Required**: Tech Lead, QA Lead  
**Ready for**: Implementation (Sprint Post-MVP)  
**Last Updated**: 2025-10-01

