# Addendum: Refactoring del Servizio di Autenticazione

**Status**: Planned (Tech Debt)  
**Priority**: Medium  
**Date**: 2025-10-01  
**Scope**: Disaccoppiamento logica di autenticazione da Supabase client  
**Epic**: Post-MVP Enhancements

---

## 1. Contesto e Motivazione

### 1.1 Problema Attuale

L'architettura corrente presenta accoppiamento diretto tra componenti React e il client Supabase:

```typescript
// Componente dipende direttamente da implementazione Supabase
import { supabase } from '@/lib/supabaseClient';

function AdminGuard({ children }) {
  useEffect(() => {
    supabase.auth.getSession().then(/* ... */);
  }, []);
}
```

**Conseguenze**:
- **Testing fragile**: necessità di doppia navigazione e mock complessi nei test E2E
- **Accoppiamento forte**: impossibile sostituire provider senza refactoring massivo
- **Violazione DIP**: componenti dipendono da dettagli implementativi, non da astrazioni
- **Manutenibilità ridotta**: logica di autenticazione dispersa in molteplici componenti

### 1.2 Obiettivi del Refactoring

- Introdurre layer di astrazione tra componenti e provider di autenticazione
- Semplificare testing eliminando pattern di doppia navigazione
- Applicare principio di Dependency Inversion
- Preparare architettura per future migrazioni (Auth0, Clerk, AWS Cognito)
- Ridurre complessità nei test E2E da ~50 righe a ~15 righe per test

---

## 2. Architettura Proposta

### 2.1 Diagramma delle Dipendenze

**Prima del Refactoring**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ AdminGuard  │────▶│  supabase   │────▶│  Supabase   │
└─────────────┘     │   client    │     │   Remote    │
                    └─────────────┘     └─────────────┘
┌─────────────┐            │
│ AuthGuard   │────────────┘
└─────────────┘
```

**Dopo il Refactoring**:
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ AdminGuard  │────▶│AuthService  │────▶│  supabase   │────▶│  Supabase   │
└─────────────┘     │ (Interface) │     │   client    │     │   Remote    │
┌─────────────┐     └─────────────┘     └─────────────┘     └─────────────┘
│ AuthGuard   │────────────┘
└─────────────┘

Test Mock:
┌─────────────┐     ┌─────────────┐
│ Test Spec   │────▶│ MockAuth    │ (vi.mock)
└─────────────┘     │ Service     │
                    └─────────────┘
```

### 2.2 Principi Architetturali

- **Dependency Inversion**: componenti dipendono da `AuthService`, non da Supabase
- **Single Responsibility**: `AuthService` gestisce solo autenticazione
- **Open/Closed**: estensibile (nuovi provider) senza modificare consumatori
- **Interface Segregation**: metodi essenziali esposti (`getSession`, `onAuthStateChange`)

---

## 3. Design del Servizio

### 3.1 Struttura File

```
apps/web/src/
├── services/
│   ├── authService.ts          # Interfaccia e implementazione
│   └── __tests__/
│       └── authService.test.ts # Unit test del servizio
├── lib/
│   └── supabaseClient.ts       # Client Supabase (non esportato direttamente)
└── components/
    ├── AdminGuard.tsx          # Consuma authService
    └── AuthGuard.tsx           # Consuma authService
```

### 3.2 Implementazione AuthService

**File**: `apps/web/src/services/authService.ts`

```typescript
import { supabase } from '@/lib/supabaseClient';
import type { Session, AuthChangeEvent } from '@supabase/supabase-js';

/**
 * Interfaccia per il servizio di autenticazione.
 * Definisce contratto indipendente dal provider.
 */
export interface IAuthService {
  getSession(): Promise<{ data: { session: Session | null }; error: any }>;
  onAuthStateChange(
    callback: (event: AuthChangeEvent, session: Session | null) => void
  ): { data: { subscription: { unsubscribe: () => void } } };
}

/**
 * Implementazione del servizio di autenticazione con Supabase.
 * Wrapper che disaccoppia l'applicazione dal client Supabase.
 */
class AuthService implements IAuthService {
  private client = supabase;

  /**
   * Recupera la sessione corrente dell'utente.
   * @returns Promise contenente dati sessione o errore
   */
  async getSession(): Promise<{ data: { session: Session | null }; error: any }> {
    return this.client.auth.getSession();
  }

  /**
   * Registra callback per cambiamenti di stato autenticazione.
   * @param callback - Funzione chiamata ad ogni cambio stato
   * @returns Oggetto subscription per cleanup
   */
  onAuthStateChange(
    callback: (event: AuthChangeEvent, session: Session | null) => void
  ) {
    return this.client.auth.onAuthStateChange(callback);
  }

  /**
   * Verifica se la sessione corrente appartiene a un admin.
   * @param session - Oggetto sessione da verificare
   * @returns true se utente è admin
   */
  isAdmin(session: Session | null): boolean {
    const role = session?.user?.user_metadata?.role as string | undefined;
    return role === 'admin';
  }

  /**
   * Verifica se la sessione corrente appartiene a uno studente.
   * @param session - Oggetto sessione da verificare
   * @returns true se utente è student
   */
  isStudent(session: Session | null): boolean {
    const role = session?.user?.user_metadata?.role as string | undefined;
    return role === 'student';
  }

  /**
   * Verifica se esiste una sessione autenticata valida.
   * @param session - Oggetto sessione da verificare
   * @returns true se sessione valida
   */
  isAuthenticated(session: Session | null): boolean {
    return session !== null;
  }
}

// Singleton instance per utilizzo globale
export const authService = new AuthService();
```

---

## 4. Migrazione Componenti Esistenti

### 4.1 AdminGuard - Prima del Refactoring

**File**: `apps/web/src/components/AdminGuard.tsx` (Versione Attuale)

```typescript
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabaseClient";
import type { Session } from "@supabase/supabase-js";

const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const isAdmin = (s: Session | null) => {
    const role = s?.user?.user_metadata?.role as string | undefined;
    return role === "admin";
  };

  useEffect(() => {
    if (!loading) {
      if (!session || !isAdmin(session)) {
        navigate("/");
      }
    }
  }, [loading, session, navigate]);

  if (loading || !session || !isAdmin(session)) {
    return <div>Verifica autorizzazione amministratore...</div>;
  }

  return <>{children}</>;
};

export default AdminGuard;
```

### 4.2 AdminGuard - Dopo il Refactoring

**File**: `apps/web/src/components/AdminGuard.tsx` (Versione Refactored)

```typescript
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/authService";
import type { Session } from "@supabase/supabase-js";

const AdminGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Utilizzo AuthService invece di supabase direttamente
    const {
      data: { subscription },
    } = authService.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    authService.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!loading) {
      // Utilizzo metodo helper del servizio
      if (!session || !authService.isAdmin(session)) {
        navigate("/");
      }
    }
  }, [loading, session, navigate]);

  if (loading || !session || !authService.isAdmin(session)) {
    return <div>Verifica autorizzazione amministratore...</div>;
  }

  return <>{children}</>;
};

export default AdminGuard;
```

**Modifiche Chiave**:
- `import { supabase }` → `import { authService }`
- `supabase.auth.getSession()` → `authService.getSession()`
- `supabase.auth.onAuthStateChange()` → `authService.onAuthStateChange()`
- `isAdmin(session)` → `authService.isAdmin(session)`

### 4.3 AuthGuard - Dopo il Refactoring

**File**: `apps/web/src/components/AuthGuard.tsx` (Versione Refactored)

```typescript
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../services/authService";
import type { Session } from "@supabase/supabase-js";

const AuthGuard: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const {
      data: { subscription },
    } = authService.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    authService.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!loading && !authService.isAuthenticated(session)) {
      navigate("/");
    }
  }, [loading, session, navigate]);

  if (loading || !authService.isAuthenticated(session)) {
    return <div>Verifica autenticazione...</div>;
  }

  return <>{children}</>;
};

export default AuthGuard;
```

---

## 5. Nuovo Pattern di Testing Semplificato

### 5.1 Test E2E - Prima del Refactoring

**Complessità**: ~50 righe, doppia navigazione, `waitForFunction`, `page.evaluate`

```typescript
test("admin autenticato naviga a /admin/debug", async ({ page }) => {
  await mockSupabaseAuth(page, "admin");
  
  // Prima navigazione
  await page.goto("/admin/debug", { waitUntil: "domcontentloaded" });
  
  // Aspetta window.supabase
  await page.waitForFunction(() => (window as any).supabase != null, {
    timeout: 5000,
  });
  
  // Mock runtime
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
  
  // Seconda navigazione
  await page.goto("/admin/debug", { waitUntil: "networkidle" });
  
  await expect(page.getByRole("heading", { name: /Debug RAG/i })).toBeVisible();
});
```

### 5.2 Test E2E - Dopo il Refactoring

**Complessità**: ~20 righe, navigazione singola, mock standard

```typescript
import { test, expect } from "@playwright/test";

test("admin autenticato naviga a /admin/debug", async ({ page }) => {
  // Mock authService e token per API
  await page.addInitScript(() => {
    const mockSession = {
      access_token: "mock-admin-token",
      user: {
        id: "test-user-id",
        aud: "authenticated",
        role: "authenticated",
        email: "admin@test.com",
        user_metadata: { role: "admin" },
      },
    };

    (window as any).__mockAuthService = {
      getSession: async () => ({ data: { session: mockSession }, error: null }),
      onAuthStateChange: (callback: any) => {
        setTimeout(() => callback("SIGNED_IN", mockSession), 0);
        return { data: { subscription: { unsubscribe: () => {} } } };
      },
      isAdmin: () => true,
      isStudent: () => false,
      isAuthenticated: () => true,
    };

    // Token per apiClient
    sessionStorage.setItem("temp_jwt", "mock-admin-token");
  });

  // Navigazione singola
  await page.goto("/admin/debug");
  
  // Assertion immediata
  await expect(page.getByRole("heading", { name: /Debug RAG/i })).toBeVisible();
});
```

### 5.3 Test Unit (Componente) - Dopo il Refactoring

**File**: `apps/web/src/components/__tests__/AdminGuard.test.tsx`

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi } from "vitest";
import AdminGuard from "../AdminGuard";
import { authService } from "../../services/authService";

// Mock del servizio
vi.mock("../../services/authService", () => ({
  authService: {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    isAdmin: vi.fn(),
  },
}));

describe("AdminGuard", () => {
  it("renderizza children quando sessione admin valida", async () => {
    const mockSession = {
      user: {
        user_metadata: { role: "admin" },
      },
    };

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    vi.mocked(authService.onAuthStateChange).mockReturnValue({
      data: {
        subscription: {
          unsubscribe: vi.fn(),
        },
      },
    });

    vi.mocked(authService.isAdmin).mockReturnValue(true);

    render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("redirige quando sessione non è admin", async () => {
    const mockSession = {
      user: {
        user_metadata: { role: "student" },
      },
    };

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    vi.mocked(authService.isAdmin).mockReturnValue(false);

    const { container } = render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
    });
  });
});
```

### 5.4 Vantaggi del Nuovo Pattern

- **Nessuna doppia navigazione**: test eseguiti ~2x più velocemente
- **Mock standard**: utilizzo di `vi.mock` come best practice Vitest
- **Meno fragilità**: nessun `setTimeout`, `waitForFunction`, `page.evaluate`
- **Più leggibile**: logica test lineare e comprensibile
- **Manutenibilità**: pattern riutilizzabile e documentato

---

## 6. Piano di Implementazione

### 6.1 Fasi di Esecuzione

**Fase 1: Creazione Servizio** (Durata: 1 giorno)
- [ ] Creare `apps/web/src/services/authService.ts`
- [ ] Implementare interfaccia `IAuthService`
- [ ] Implementare classe `AuthService`
- [ ] Scrivere unit test per `authService`

**Fase 2: Migrazione Componenti** (Durata: 1 giorno)
- [ ] Refactorizzare `AdminGuard.tsx`
- [ ] Refactorizzare `AuthGuard.tsx`
- [ ] Verificare nessuna regressione visuale

**Fase 3: Aggiornamento Test** (Durata: 2 giorni)
- [ ] Riscrivere test E2E `story-4.1.spec.ts`
- [ ] Riscrivere test E2E per Story 1.2, 1.3, 3.3
- [ ] Creare test unit per `AdminGuard` e `AuthGuard`
- [ ] Validare coverage > 80%

**Fase 4: Cleanup e Documentazione** (Durata: 0.5 giorni)
- [ ] Rimuovere `window.supabase` exposure da `supabaseClient.ts`
- [ ] Eliminare helper `authMock.ts` obsoleto
- [ ] Aggiornare `addendum-e2e-auth-mocking.md`
- [ ] Creare migration guide per team

### 6.2 Checklist di Validazione

**Pre-Refactoring**:
- [ ] Tutti i test esistenti passano (baseline)
- [ ] Coverage corrente documentato
- [ ] Branch feature creato da `master`

**Post-Refactoring**:
- [ ] Tutti i test passano (nessuna regressione)
- [ ] Coverage >= 80% su authService
- [ ] Nessun import diretto di `supabase` nei componenti
- [ ] Test E2E eseguiti in < 1 minuto
- [ ] Zero flaky test su 10 run consecutive

---

## 7. Gestione del Rischio

### 7.1 Rischi Identificati

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| Regressione Story 1.2, 1.3, 3.3 | Alta | Alto | Test E2E completi prima del merge |
| Breaking change in produzione | Bassa | Critico | Deploy graduale, feature flag |
| Performance degradation | Bassa | Medio | Benchmark prima/dopo |
| Team onboarding su nuovo pattern | Media | Basso | Training session + migration guide |

### 7.2 Strategia di Rollback

In caso di problemi critici:

1. Revert commit di merge
2. Ripristinare branch `master` precedente
3. Re-deploy versione stabile
4. Post-mortem per analisi fallimento

---

## 8. Metriche di Successo

### 8.1 Metriche Tecniche

- **Coverage**: >= 80% su authService, AdminGuard, AuthGuard
- **Performance Test E2E**: riduzione >= 40% tempo esecuzione
- **Complessità Ciclomatica**: AdminGuard <= 5, AuthGuard <= 5
- **Linee di codice Test**: riduzione >= 50% per test E2E

### 8.2 Metriche di Qualità

- **Zero regressioni funzionali** validate da test E2E
- **Zero dipendenze dirette** da supabase nei componenti
- **100% conformità** a principio Dependency Inversion
- **Documentazione completa** con esempi e migration guide

---

## 9. Dipendenze e Prerequisiti

### 9.1 Dipendenze Tecniche

- TypeScript >= 5.0
- Vitest configurato per unit test
- Playwright configurato per E2E test
- React Router >= 6.0

### 9.2 Prerequisiti Organizzativi

- Approvazione Tech Lead
- Approvazione Product Owner
- Sprint dedicato a Tech Debt
- Testing environment disponibile
- CI/CD pipeline funzionante

---

## 10. Estensioni Future

### 10.1 Provider Alternativi

Con `IAuthService`, sostituire provider diventa triviale:

```typescript
// apps/web/src/services/auth0Service.ts
class Auth0Service implements IAuthService {
  async getSession() {
    // Implementazione Auth0
  }
  
  onAuthStateChange(callback) {
    // Implementazione Auth0
  }
}

// Cambio in un solo punto
export const authService = new Auth0Service();
```

### 10.2 Funzionalità Aggiuntive

Possibili estensioni al servizio:
- `signIn(email, password)`: autenticazione
- `signOut()`: logout
- `resetPassword(email)`: recupero password
- `updateProfile(data)`: aggiornamento profilo
- `refreshToken()`: refresh automatico token

---

## 11. Riferimenti

- **Issue**: GitHub Issue #TBD
- **Epic**: Tech Debt - Post-MVP Enhancements
- **Story**: Story TBD - Refactoring Auth Service
- **Documento Collegato**: `addendum-e2e-auth-mocking.md` (problema originale)
- **Team Discussion**: `4.1-team-discussion-points-20251001.md` (Opzione B)
- **Dependency Inversion Principle**: https://en.wikipedia.org/wiki/Dependency_inversion_principle

---

**Status**: ✅ Documentato - In attesa di approvazione per implementazione  
**Prepared by**: AI Development Team  
**Review Required**: Tech Lead, Senior Developer, QA Lead  
**Target Sprint**: Post-MVP Sprint 1  
**Ultimo Aggiornamento**: 2025-10-01

