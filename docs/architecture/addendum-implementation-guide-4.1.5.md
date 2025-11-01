# Addendum: Implementation Guide for Story 4.1.5 — Admin Dashboard Hub

**Date**: 2025-10-01  
**Scope**: Story 4.1.5 Technical Implementation  
**Audience**: Development Team  
**Type**: Best Practices & Quick Reference

---

## Document Purpose

Guida operativa per implementazione Story 4.1.5 (Admin Dashboard Hub) che integra:
- Soluzioni ai rischi critici identificati (R-4.1.5-1 BLOCKER: Card component)
- Pattern di implementazione validati dalle documentazioni ufficiali
- Quick reference per accelerare sviluppo e testing

**Context**: Risk Profile 4.1.5 ha identificato Shadcn/UI Card component come **CRITICAL BLOCKER** (R-4.1.5-1). Questa guida fornisce procedure operative per risoluzione blocker e implementazione conforme story requirements.

[Fonti: `docs/qa/assessments/4.1.5-risk-20251001.md`, `docs/stories/4.1.5-admin-dashboard-hub.md`]

---

## Section 1: CRITICAL — Card Component Installation

### 1.1 Problem Statement

**Risk ID**: R-4.1.5-1  
**Severity**: CRITICAL  
**Status**: BLOCKER

Story 4.1.5 assume disponibilità componente `Card` da Shadcn/UI, ma verifica codebase conferma assenza:
- File `apps/web/src/components/ui/card.tsx` non esiste
- Nessun import `Card` nel progetto
- Implementazione bloccata senza componente

[Fonte: `docs/qa/assessments/4.1.5-risk-20251001.md` L49-91]

---

### 1.2 Resolution Procedure

#### Step 1: Installation

**Command** (eseguire da `apps/web/`):
```bash
pnpm dlx shadcn@latest add card
```

**Expected Output**:
```
✔ Done. Card component added to your project.
```

**Verification**:
```bash
# Verificare file creato
ls -la src/components/ui/card.tsx

# Output atteso: file esiste con timestamp recente
```

[Fonte: Shadcn/UI Official Documentation — https://ui.shadcn.com/docs/components/card]

---

#### Step 2: Component Structure Verification

**File**: `apps/web/src/components/ui/card.tsx`

**Expected Exports**:
```typescript
export { Card }           // Container principale
export { CardHeader }     // Header section
export { CardTitle }      // Titolo card
export { CardDescription } // Sottotitolo/descrizione
export { CardContent }    // Body content (opzionale)
export { CardFooter }     // Footer section (opzionale)
```

**Import Test** (TypeScript compilation check):
```typescript
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
```

**Success Criteria**: Zero TypeScript errors su import.

---

#### Step 3: Isolated Rendering Test

**Purpose**: Verificare Card rendering corretto con Tailwind classes prima integration DashboardPage.

**Test File**: `apps/web/src/components/ui/__tests__/card.test.tsx` (optional)

```typescript
import { render, screen } from '@testing-library/react'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

describe('Card Component', () => {
  it('renders card with title and description', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Title</CardTitle>
          <CardDescription>Test Description</CardDescription>
        </CardHeader>
      </Card>
    )
    
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test Description')).toBeInTheDocument()
  })
})
```

**Success Criteria**: Test PASS, Card renders con Tailwind styling.

[Fonte: Test Design 4.1.5 PRE-IMPL-002]

---

### 1.3 Usage Pattern for Story 4.1.5

#### Basic Card Structure

```tsx
import { Link } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

export default function DashboardPage() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {/* Card Debug RAG */}
      <Link to="/admin/debug" aria-label="Vai a Debug RAG">
        <Card className="hover:bg-accent transition-colors">
          <CardHeader>
            <CardTitle>Debug RAG</CardTitle>
            <CardDescription>
              Visualizza chunk recuperati e risposte LLM per query di test
            </CardDescription>
          </CardHeader>
        </Card>
      </Link>
      
      {/* Card Analytics (Disabled pre-Story 4.2) */}
      <Card className="opacity-60 cursor-not-allowed">
        <CardHeader>
          <CardTitle>
            Analytics Dashboard
            <span className="ml-2 text-xs text-muted-foreground">Coming Soon</span>
          </CardTitle>
          <CardDescription>
            Statistiche utilizzo, domande frequenti, distribuzione argomenti
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
```

**Key Points**:
- Link wrapper per card navigabili (Debug RAG)
- Disabled state per card non funzionali (Analytics pre-4.2)
- Aria-label per accessibilità
- Hover effect per feedback visivo

[Fonte: Story 4.1.5 L58-83, Risk 4.1.5 R-4.1.5-2 mitigation]

---

#### Disabled Card Pattern (Analytics pre-Story 4.2)

**Problem**: Card Analytics non deve navigare a `/admin/analytics` (route non esiste pre-Story 4.2).

**Solution**:
```tsx
{/* Opzione 1: Disabled con badge */}
<Card className="opacity-60 cursor-not-allowed" aria-disabled="true">
  <CardHeader>
    <CardTitle className="flex items-center gap-2">
      Analytics Dashboard
      <span className="inline-flex items-center rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
        Coming Soon
      </span>
    </CardTitle>
    <CardDescription>Disponibile dopo Story 4.2</CardDescription>
  </CardHeader>
</Card>

{/* Opzione 2: Con Badge component Shadcn/UI */}
import { Badge } from "@/components/ui/badge"

<Card className="opacity-60 cursor-not-allowed">
  <CardHeader>
    <CardTitle>
      Analytics Dashboard
      <Badge variant="outline" className="ml-2">Coming Soon</Badge>
    </CardTitle>
  </CardHeader>
</Card>
```

**CSS Classes**:
- `opacity-60`: riduce opacità per stato disabled
- `cursor-not-allowed`: cursor visivo disabled
- `aria-disabled="true"`: accessibilità screen reader

[Fonte: Risk 4.1.5 R-4.1.5-2 L117-140]

---

### 1.4 Alternative Approach (Fallback)

**Scenario**: Installazione Card fallisce o blocca timeline.

**Solution**: Pattern `div` custom con Tailwind (già validato in ChunkCard).

```tsx
<div className="rounded-lg border border-border bg-card p-4 hover:bg-accent transition-colors">
  <Link to="/admin/debug" className="block space-y-1">
    <h3 className="text-lg font-semibold text-card-foreground">Debug RAG</h3>
    <p className="text-sm text-muted-foreground">
      Visualizza chunk recuperati e risposte LLM per query di test
    </p>
  </Link>
</div>
```

**Trade-offs**:
- ✅ Zero nuove dependencies
- ✅ Pattern già validato (ChunkCard L37-58)
- ❌ Meno componibile
- ❌ Futura migrazione Card richiede rework

**Recommendation**: Usare solo se installazione Card blocca timeline (risk acceptance).

[Fonte: Risk 4.1.5 Alternative Approach L632-651]

---

## Section 2: Responsive Grid Layout

### 2.1 Tailwind CSS Grid Responsive Pattern

**Requirement**: AC4 — "Layout responsive: grid 2 col desktop, 1 col mobile"

**Implementation**:
```tsx
<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
  {/* Card 1 */}
  {/* Card 2 */}
</div>
```

**Behavior**:
- **Mobile** (< 768px): `grid-cols-1` → 1 colonna (default mobile-first)
- **Desktop** (≥ 768px): `md:grid-cols-2` → 2 colonne affiancate
- **Gap**: `gap-4` → 1rem spacing tra card

**Breakpoint Reference**:
- `md`: 768px (48rem) — Tablet/Desktop
- Pattern Tailwind: mobile-first, override con breakpoint prefix

[Fonte: Tailwind CSS Official — https://tailwindcss.com/docs/responsive-design]

---

### 2.2 Testing Responsive Behavior

#### Unit Test (Vitest)

```typescript
import { render } from '@testing-library/react'
import DashboardPage from '../DashboardPage'

describe('DashboardPage Responsive', () => {
  it('has correct responsive grid classes', () => {
    const { container } = render(<DashboardPage />)
    const gridContainer = container.querySelector('.grid')
    
    expect(gridContainer).toHaveClass('grid-cols-1')
    expect(gridContainer).toHaveClass('md:grid-cols-2')
    expect(gridContainer).toHaveClass('gap-4')
  })
})
```

[Fonte: Test Design 4.1.5 UT-4.1.5-010]

---

#### E2E Test (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test.describe('Responsive Layout', () => {
  test('mobile viewport: 1 column layout', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    await page.goto('/admin/dashboard')
    
    // Verify card stacking (1 column)
    const cards = await page.locator('[role="link"]').all()
    expect(cards.length).toBeGreaterThan(0)
    
    // Visual verification: screenshot mobile
    await page.screenshot({ path: 'dashboard-mobile.png' })
  })
  
  test('desktop viewport: 2 column layout', async ({ page }) => {
    // Set desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 })
    
    await page.goto('/admin/dashboard')
    
    // Visual verification: screenshot desktop
    await page.screenshot({ path: 'dashboard-desktop.png' })
  })
})
```

**Viewport Standards**:
- **Mobile**: 375x667 (iPhone SE standard)
- **Desktop**: 1280x720 (common laptop resolution)

[Fonte: Playwright Official — https://playwright.dev/docs/emulation, Test Design 4.1.5 E2E-4.1.5-007/008]

---

### 2.3 Manual Testing (Chrome DevTools)

**Procedure**:
1. Aprire dashboard in browser
2. `F12` → Toggle Device Toolbar (`Ctrl+Shift+M`)
3. Selezionare device preset: "iPhone SE" (375px)
4. Verificare: card in colonna singola, no scroll orizzontale
5. Selezionare "Responsive" e resize a 1280px
6. Verificare: card affiancate in 2 colonne

**Success Criteria**: Layout fluido, nessun overflow, spacing corretto.

---

## Section 3: React Router Navigation

### 3.1 Link Component Usage

**Requirement**: AC6 — "Navigazione tra funzionalità admin non richiede browser back (link diretti)"

**Implementation**:
```tsx
import { Link } from "react-router-dom"

<Link to="/admin/debug" aria-label="Vai a Debug RAG">
  <Card>
    {/* Card content */}
  </Card>
</Link>
```

**Key Points**:
- `to` prop: client-side navigation path
- `aria-label`: descrizione accessibile per screen reader
- Link wrapper Card: intera card cliccabile (UX best practice)

[Fonte: React Router Official — https://reactrouter.com/api/components/Link]

---

### 3.2 Testing Navigation

#### Unit Test (Vitest + React Testing Library)

```typescript
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from '../DashboardPage'

describe('Navigation Links', () => {
  it('has correct href for Debug RAG card', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )
    
    const debugLink = screen.getByRole('link', { name: /vai a debug rag/i })
    expect(debugLink).toHaveAttribute('href', '/admin/debug')
  })
  
  it('has aria-label for accessibility', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    )
    
    const debugLink = screen.getByRole('link', { name: /vai a debug rag/i })
    expect(debugLink).toHaveAttribute('aria-label', 'Vai a Debug RAG')
  })
})
```

[Fonte: Test Design 4.1.5 UT-4.1.5-004, UT-4.1.5-013]

---

#### E2E Test (Playwright)

```typescript
import { test, expect } from '@playwright/test'

test('navigation from dashboard to debug', async ({ page }) => {
  // Setup admin session
  await page.addInitScript(() => {
    (window as any).__mockAuthService = {
      getSession: async () => ({ data: { session: mockAdminSession }, error: null }),
      isAdmin: () => true,
    }
  })
  
  await page.goto('/admin/dashboard')
  
  // Click Debug RAG card
  await page.click('text=Debug RAG')
  
  // Verify navigation
  await expect(page).toHaveURL('/admin/debug')
  await expect(page.locator('h1:has-text("Debug RAG")')).toBeVisible()
})
```

[Fonte: Test Design 4.1.5 E2E-4.1.5-002]

---

## Section 4: User Info Display with Fallback

### 4.1 Session Email Extraction

**Requirement**: AC3 — "Dashboard mostra informazioni utente admin (email, ruolo)"  
**Risk**: R-4.1.5-3 — Session email extraction failure

**Problem**: Email potrebbe essere undefined (race condition, auth provider esterni).

**Solution**: Pattern loading state + fallback.

---

### 4.2 Implementation Pattern

```tsx
import { useState, useEffect } from 'react'
import { authService } from '@/services/authService'
import type { Session } from '@supabase/supabase-js'

export default function DashboardPage() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    authService.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })
  }, [])
  
  if (loading) {
    return <div>Caricamento dashboard...</div>
  }
  
  // Safe email extraction with fallback
  const userEmail = session?.user?.email || "Amministratore"
  
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Dashboard Amministratore</h1>
        <p className="text-sm text-muted-foreground">
          Benvenuto, {userEmail}
        </p>
      </div>
      
      {/* Grid funzionalità admin */}
    </div>
  )
}
```

**Key Features**:
- Loading state pattern (replicato da AdminGuard)
- Optional chaining: `session?.user?.email`
- Nullish coalescing: `|| "Amministratore"` (fallback)

[Fonte: Risk 4.1.5 R-4.1.5-3 L169-194]

---

### 4.3 Testing Email Fallback

#### Unit Tests (Vitest)

```typescript
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import DashboardPage from '../DashboardPage'

vi.mock('@/services/authService')

describe('User Email Display', () => {
  it('displays email from session', async () => {
    const mockSession = {
      user: { id: '123', email: 'admin@test.com', user_metadata: { role: 'admin' } }
    }
    
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null
    })
    
    render(<DashboardPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/benvenuto, admin@test.com/i)).toBeInTheDocument()
    })
  })
  
  it('displays fallback when session null', async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: null },
      error: null
    })
    
    render(<DashboardPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/benvenuto, amministratore/i)).toBeInTheDocument()
    })
  })
  
  it('displays fallback when email undefined', async () => {
    const mockSession = {
      user: { id: '123', email: undefined, user_metadata: { role: 'admin' } }
    }
    
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null
    })
    
    render(<DashboardPage />)
    
    await waitFor(() => {
      expect(screen.getByText(/benvenuto, amministratore/i)).toBeInTheDocument()
    })
  })
})
```

[Fonte: Vitest Official — https://vitest.dev/guide/mocking, Test Design 4.1.5 UT-4.1.5-007/008/009]

---

## Section 5: Testing Patterns Reference

### 5.1 Vitest Mock Pattern (authService)

**Purpose**: Isolare DashboardPage da dipendenze esterne per unit testing.

**Pattern**:
```typescript
import { vi } from 'vitest'

// Mock intero modulo authService
vi.mock('@/services/authService', () => ({
  authService: {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    isAdmin: vi.fn(),
    isStudent: vi.fn(),
    isAuthenticated: vi.fn(),
  }
}))

// Configurare mock behavior per test specifico
import { authService } from '@/services/authService'

vi.mocked(authService.getSession).mockResolvedValue({
  data: { session: mockAdminSession },
  error: null
})

vi.mocked(authService.isAdmin).mockReturnValue(true)
```

**Key Points**:
- `vi.mock()`: sostituisce modulo con mock
- `vi.fn()`: crea funzione mock tracciabile
- `vi.mocked()`: type-safe access a mock functions
- `mockResolvedValue()`: mock async function return

[Fonte: Vitest Official — https://vitest.dev/guide/mocking]

---

### 5.2 Playwright Mock Pattern (E2E Auth)

**Purpose**: Simulare autenticazione admin in test E2E senza backend reale.

**Pattern** (da Story 4.1 refactoring):
```typescript
import { test, expect } from '@playwright/test'

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Inject mock authService nel browser context
    await page.addInitScript(() => {
      const mockSession = {
        user: {
          id: 'mock-admin-id',
          email: 'admin@test.com',
          user_metadata: { role: 'admin' },
        },
      }
      
      // Mock global authService
      (window as any).__mockAuthService = {
        getSession: async () => ({ 
          data: { session: mockSession }, 
          error: null 
        }),
        onAuthStateChange: (callback) => {
          setTimeout(() => callback('SIGNED_IN', mockSession), 0)
          return { data: { subscription: { unsubscribe: () => {} } } }
        },
        isAdmin: () => true,
        isStudent: () => false,
        isAuthenticated: () => true,
      }
      
      // Mock JWT token per apiClient
      sessionStorage.setItem('temp_jwt', 'mock-admin-token')
    })
  })
  
  test('admin can access dashboard', async ({ page }) => {
    await page.goto('/admin/dashboard')
    
    await expect(page.locator('h1:has-text("Dashboard Amministratore")')).toBeVisible()
    await expect(page.locator('text=admin@test.com')).toBeVisible()
  })
})
```

**Key Features**:
- `page.addInitScript()`: esegue script prima page load
- `__mockAuthService`: pattern riconosciuto da `authService.ts`
- `sessionStorage` mock: simula JWT token persistente

[Fonte: Story 4.1 Tech Debt Auth Refactoring L298-318, Test Design 4.1.5]

---

### 5.3 Playwright Viewport Configuration

**Purpose**: Testare responsive behavior mobile/desktop.

**Pattern**:
```typescript
import { test } from '@playwright/test'

// Opzione 1: Per tutti i test nel file
test.use({
  viewport: { width: 375, height: 667 }
})

test('test mobile', async ({ page }) => {
  // Viewport già configurato 375x667
})

// Opzione 2: Per test specifico
test('test responsive', async ({ page }) => {
  // Mobile
  await page.setViewportSize({ width: 375, height: 667 })
  await page.screenshot({ path: 'mobile.png' })
  
  // Desktop
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.screenshot({ path: 'desktop.png' })
})
```

**Viewport Standards**:
| Device | Width | Height | Use Case |
|--------|-------|--------|----------|
| iPhone SE | 375px | 667px | Mobile testing standard |
| iPad | 768px | 1024px | Tablet (breakpoint validation) |
| Desktop | 1280px | 720px | Common laptop resolution |
| Desktop HD | 1920px | 1080px | High-res desktop |

[Fonte: Playwright Official — https://playwright.dev/docs/emulation]

---

## Section 6: Pre-Implementation Checklist

### 6.1 Environment Setup

**Prerequisites**:
- [ ] Node.js ≥18 installato
- [ ] pnpm ≥8 installato
- [ ] Repository clonato e dependencies installate (`pnpm install`)
- [ ] Vitest configurato (`apps/web/vitest.config.ts` presente)
- [ ] Playwright configurato (`apps/web/playwright.config.ts` presente)

---

### 6.2 CRITICAL — Card Component Installation

**BLOCKER**: R-4.1.5-1

- [ ] **Eseguire**: `cd apps/web && pnpm dlx shadcn@latest add card`
- [ ] **Verificare**: File `src/components/ui/card.tsx` esiste
- [ ] **Test Import**: TypeScript compilation zero errors
- [ ] **Test Rendering**: Card renders con Tailwind styling (optional unit test)

**Gating Condition**: Implementation Story 4.1.5 bloccata fino completamento checklist.

---

### 6.3 Pattern Validation

**Reference Implementations**:
- [ ] ChunkCard pattern studiato (`apps/web/src/components/ChunkCard.tsx`)
- [ ] AdminGuard pattern studiato (`apps/web/src/components/AdminGuard.tsx`)
- [ ] Story 4.1 mock auth pattern studiato (`apps/web/tests/story-4.1.spec.ts`)

---

## Section 7: Common Pitfalls & Solutions

### 7.1 Card Component Import Error

**Symptom**:
```
Error: Module '"@/components/ui/card"' has no exported member 'Card'
```

**Cause**: Card component non installato.

**Solution**: Eseguire installation procedure (Section 1.2).

---

### 7.2 Link Causing Full Page Reload

**Symptom**: Click card → full page reload invece client-side navigation.

**Cause**: Usato `<a>` invece `<Link>`.

**Solution**:
```tsx
// ❌ Wrong
<a href="/admin/debug">Debug RAG</a>

// ✅ Correct
import { Link } from "react-router-dom"
<Link to="/admin/debug">Debug RAG</Link>
```

---

### 7.3 Email Undefined Crash

**Symptom**: `Cannot read property 'email' of undefined` runtime error.

**Cause**: Session email access non safe.

**Solution**: Usare optional chaining + fallback (Section 4.2).

```tsx
// ❌ Unsafe
<p>Benvenuto, {session.user.email}</p>

// ✅ Safe
<p>Benvenuto, {session?.user?.email || "Amministratore"}</p>
```

---

### 7.4 Mobile Layout Overflow

**Symptom**: Card tagliate su mobile, scroll orizzontale.

**Cause**: Mancanza `grid-cols-1` default class.

**Solution**:
```tsx
// ❌ Wrong (assume 2 col default)
<div className="grid md:grid-cols-2">

// ✅ Correct (mobile-first: 1 col default, 2 col desktop)
<div className="grid grid-cols-1 md:grid-cols-2">
```

---

### 7.5 Test Flaky: Session Not Loaded

**Symptom**: E2E test intermittent failure, email non mostrata.

**Cause**: Race condition, session load async non awaited.

**Solution**: Usare explicit wait in test.
```typescript
// ❌ Flaky
await page.goto('/admin/dashboard')
await expect(page.locator('text=admin@test.com')).toBeVisible()

// ✅ Robust
await page.goto('/admin/dashboard')
await page.waitForLoadState('networkidle')
await expect(page.locator('text=admin@test.com')).toBeVisible({ timeout: 5000 })
```

---

## Section 8: Integration with Story 4.2

### 8.1 Card Analytics Enablement

**Context**: Post-merge Story 4.2, card Analytics deve essere abilitata.

**Current State** (Story 4.1.5):
```tsx
<Card className="opacity-60 cursor-not-allowed">
  <CardHeader>
    <CardTitle>
      Analytics Dashboard
      <Badge>Coming Soon</Badge>
    </CardTitle>
  </CardHeader>
</Card>
```

**Updated State** (Story 4.2):
```tsx
<Link to="/admin/analytics" aria-label="Vai ad Analytics Dashboard">
  <Card className="hover:bg-accent transition-colors">
    <CardHeader>
      <CardTitle>Analytics Dashboard</CardTitle>
      <CardDescription>
        Statistiche utilizzo, domande frequenti, distribuzione argomenti
      </CardDescription>
    </CardHeader>
  </Card>
</Link>
```

**Changes Required**:
1. Rimuovere classes disabled (`opacity-60`, `cursor-not-allowed`)
2. Rimuovere badge "Coming Soon"
3. Wrappare Card con `<Link to="/admin/analytics">`
4. Aggiungere hover effect + aria-label

**Effort**: <10 LOC modificate, <5 min implementation.

[Fonte: Risk 4.1.5 R-4.1.5-6 L315-332]

---

### 8.2 Integration Test Post-4.2

**Test File**: `apps/web/tests/story-4.1.5-4.2-integration.spec.ts` (nuovo)

```typescript
test('dashboard to analytics navigation', async ({ page }) => {
  await page.goto('/admin/dashboard')
  
  // Verify badge "Coming Soon" rimosso
  await expect(page.locator('text=Coming Soon')).not.toBeVisible()
  
  // Click Analytics card
  await page.click('text=Analytics Dashboard')
  
  // Verify navigation
  await expect(page).toHaveURL('/admin/analytics')
  await expect(page.locator('h1:has-text("Analytics")')).toBeVisible()
})
```

---

## Section 9: Quick Reference Card

### Component Installation
```bash
pnpm dlx shadcn@latest add card
```

### Responsive Grid
```tsx
<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
```

### Safe Email Display
```tsx
const email = session?.user?.email || "Amministratore"
<p>Benvenuto, {email}</p>
```

### Card Navigation
```tsx
<Link to="/admin/debug" aria-label="Vai a Debug RAG">
  <Card>...</Card>
</Link>
```

### Disabled Card
```tsx
<Card className="opacity-60 cursor-not-allowed" aria-disabled="true">
  <Badge>Coming Soon</Badge>
</Card>
```

### Mock Auth (Unit Test)
```typescript
vi.mock('@/services/authService', () => ({
  authService: {
    getSession: vi.fn().mockResolvedValue({
      data: { session: mockSession },
      error: null
    }),
    isAdmin: vi.fn().mockReturnValue(true),
  }
}))
```

### Mock Auth (E2E Test)
```typescript
await page.addInitScript(() => {
  (window as any).__mockAuthService = {
    getSession: async () => ({ data: { session }, error: null }),
    isAdmin: () => true,
  }
})
```

### Viewport Testing
```typescript
await page.setViewportSize({ width: 375, height: 667 }) // Mobile
await page.setViewportSize({ width: 1280, height: 720 }) // Desktop
```

---

## References

### Story Documents
- Story 4.1.5: `docs/stories/4.1.5-admin-dashboard-hub.md`
- Risk Profile 4.1.5: `docs/qa/assessments/4.1.5-risk-20251001.md`
- Test Design 4.1.5: `docs/qa/assessments/4.1.5-test-design-20251001.md`

### Official Documentation
- Shadcn/UI Card: https://ui.shadcn.com/docs/components/card
- Tailwind Responsive: https://tailwindcss.com/docs/responsive-design
- React Router Link: https://reactrouter.com/api/components/Link
- Vitest Mocking: https://vitest.dev/guide/mocking
- Playwright Emulation: https://playwright.dev/docs/emulation

### Project References
- ChunkCard Pattern: `apps/web/src/components/ChunkCard.tsx`
- AdminGuard Pattern: `apps/web/src/components/AdminGuard.tsx`
- authService: `apps/web/src/services/authService.ts`
- Story 4.1 E2E Mock: `apps/web/tests/story-4.1.spec.ts`

---

**Last Updated**: 2025-10-01  
**Maintainer**: Development Team  
**Status**: Active Reference Document

