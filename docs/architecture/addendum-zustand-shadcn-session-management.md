# Addendum: Zustand + Shadcn/UI Session Management Patterns

**Epic:** 9 - Persistent Conversational Memory  
**Story:** 9.3 - Chat Session Management UI  
**Created:** 2025-01-17  
**Author:** Architect Agent  
**Status:** Ready for Implementation

---

## Purpose

Documentare pattern implementativi ufficiali per state management (Zustand) e UI components (Shadcn/UI) necessari per Story 9.3. Questo addendum fornisce code snippets production-ready, best practices, e pitfalls comuni per garantire implementazione sicura e performante del sistema di gestione sessioni chat.

---

## Table of Contents

1. [Zustand Store Pattern](#1-zustand-store-pattern)
2. [Shadcn Sheet Component](#2-shadcn-sheet-component)
3. [Shadcn AlertDialog](#3-shadcn-alertdialog)
4. [Shadcn DropdownMenu](#4-shadcn-dropdownmenu)
5. [Integration Checklist](#5-integration-checklist)
6. [Testing Patterns](#6-testing-patterns)
7. [Common Pitfalls](#7-common-pitfalls)

---

## 1. Zustand Store Pattern

### 1.1 Basic Store Setup con Persist Middleware

**File:** `apps/web/src/store/sessionStore.ts`

```typescript
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface SessionMetadata {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messageCount: number
}

interface SessionState {
  sessions: SessionMetadata[]
  currentSessionId: string | null
  
  // Actions
  setSessions: (sessions: SessionMetadata[]) => void
  addSession: (session: SessionMetadata) => void
  updateSession: (id: string, updates: Partial<SessionMetadata>) => void
  deleteSession: (id: string) => void
  setCurrentSession: (id: string | null) => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      
      setSessions: (sessions) => set({ sessions }),
      
      addSession: (session) => 
        set((state) => ({ 
          sessions: [session, ...state.sessions] 
        })),
      
      updateSession: (id, updates) =>
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === id ? { ...s, ...updates } : s
          ),
        })),
      
      deleteSession: (id) =>
        set((state) => ({
          sessions: state.sessions.filter((s) => s.id !== id),
          currentSessionId: 
            state.currentSessionId === id ? null : state.currentSessionId,
        })),
      
      setCurrentSession: (id) => set({ currentSessionId: id }),
    }),
    {
      name: 'chat.sessions', // localStorage key
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
)
```

**Key Points:**
- `persist` middleware abilita sync automatico con localStorage
- `partialize` escludi functions da serializzazione (solo plain data)
- `name: 'chat.sessions'` garantisce unique key (no collision con altri stores)
- Actions immutabili: sempre return nuovo state, mai mutare direttamente

---

### 1.2 Hydration Pattern (SSR/Initial Load)

**File:** `apps/web/src/hooks/useHydration.ts`

```typescript
import { useEffect, useState } from 'react'
import { useSessionStore } from '@/store/sessionStore'

export function useHydration() {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const unsubHydrate = useSessionStore.persist.onHydrate(() => 
      setHydrated(false)
    )
    const unsubFinish = useSessionStore.persist.onFinishHydration(() => 
      setHydrated(true)
    )

    setHydrated(useSessionStore.persist.hasHydrated())

    return () => {
      unsubHydrate()
      unsubFinish()
    }
  }, [])

  return hydrated
}
```

**Usage in Component:**

```typescript
function SessionList() {
  const hydrated = useHydration()
  const sessions = useSessionStore((state) => state.sessions)

  if (!hydrated) {
    return <div>Caricamento sessioni...</div>
  }

  return <div>{/* render sessions */}</div>
}
```

**Why:** Previene hydration mismatch tra server e client. Critico per garantire UI consistente durante initial load.

---

### 1.3 Performance Optimization: Selectors

```typescript
// ❌ BAD - Re-render su ogni store change
const { sessions, addSession } = useSessionStore()

// ✅ GOOD - Re-render solo quando sessions cambia
const sessions = useSessionStore((state) => state.sessions)
const addSession = useSessionStore((state) => state.addSession)

// ⭐ BEST - Con shallow equality per array/objects
import { shallow } from 'zustand/shallow'

const [sessions, addSession] = useSessionStore(
  (state) => [state.sessions, state.addSession],
  shallow
)
```

**Rule:** Sempre usare selectors specifici. Mai destructure intero state.

---

### 1.4 Outside React: getState() API

```typescript
// Access store outside React components (utils, API calls)
const currentSessions = useSessionStore.getState().sessions
useSessionStore.getState().addSession(newSession)

// Manual rehydrate
await useSessionStore.persist.rehydrate()

// Clear storage
useSessionStore.persist.clearStorage()

// Check hydration status (non-reactive)
const isHydrated = useSessionStore.persist.hasHydrated()
```

---

## 2. Shadcn Sheet Component

### 2.1 Responsive Sidebar Pattern (Mobile Sheet + Desktop Aside)

**File:** `apps/web/src/components/ChatSidebar.tsx`

```typescript
import { useState } from 'react'
import { Menu } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useSessionStore } from '@/store/sessionStore'

export function ChatSidebar() {
  const [open, setOpen] = useState(false)
  const sessions = useSessionStore((state) => state.sessions)

  const handleSessionSelect = (sessionId: string) => {
    useSessionStore.getState().setCurrentSession(sessionId)
    setOpen(false) // Auto-close on mobile
  }

  const sidebarContent = (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold">Sessioni Chat</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => handleSessionSelect(session.id)}
            className="w-full p-3 text-left rounded-lg hover:bg-accent"
          >
            <div className="font-medium">{session.title}</div>
            <div className="text-sm text-muted-foreground">
              {session.messageCount} messaggi
            </div>
          </button>
        ))}
      </div>
    </div>
  )

  return (
    <>
      {/* Mobile: Sheet overlay */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild className="lg:hidden">
          <Button variant="ghost" size="icon">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        
        <SheetContent 
          side="left" 
          className="w-[300px] sm:w-[400px] p-0"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Sessioni Chat</SheetTitle>
          </SheetHeader>
          {sidebarContent}
        </SheetContent>
      </Sheet>

      {/* Desktop: Fixed aside */}
      <aside className="hidden lg:flex w-80 border-r flex-col">
        {sidebarContent}
      </aside>
    </>
  )
}
```

**Key Points:**
- DRY pattern: `sidebarContent` riusato per mobile e desktop
- `lg:hidden` / `hidden lg:flex`: Tailwind breakpoint 1024px
- `setOpen(false)` dopo navigation garantisce UX mobile corretta
- `side="left"` per sidebar (vs `side="right"` per settings panel)

---

### 2.2 Scroll Behavior con Fixed Header/Footer

```typescript
<SheetContent side="left" className="p-0 flex flex-col">
  {/* Fixed header */}
  <div className="p-4 border-b">
    <h2>Sessioni</h2>
  </div>
  
  {/* Scrollable content */}
  <div className="flex-1 overflow-y-auto p-4">
    {sessions.map((s) => (
      <SessionItem key={s.id} session={s} />
    ))}
  </div>
  
  {/* Fixed footer (optional) */}
  <div className="p-4 border-t">
    <Button>Nuova Sessione</Button>
  </div>
</SheetContent>
```

**Why:** `flex-col` + `flex-1` + `overflow-y-auto` garantisce header/footer sticky e content scrollable.

---

### 2.3 Z-Index Management

```typescript
// Sheet default z-index: 50 (overlay), 51 (content)
// AlertDialog z-index: 52 (garantito sopra Sheet)

// Se conflitti custom:
<SheetContent className="z-[100]">
```

**Note:** Shadcn/UI gestisce z-index automaticamente per layering corretto.

---

## 3. Shadcn AlertDialog

### 3.1 Delete Confirmation Pattern con Async API

**File:** `apps/web/src/components/DeleteSessionDialog.tsx`

```typescript
import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useSessionStore } from '@/store/sessionStore'
import { toast } from 'sonner'
import apiClient from '@/lib/apiClient'

interface DeleteSessionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sessionId: string
  sessionTitle: string
}

export function DeleteSessionDialog({
  open,
  onOpenChange,
  sessionId,
  sessionTitle,
}: DeleteSessionDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const deleteSession = useSessionStore((state) => state.deleteSession)

  const handleDelete = async () => {
    setIsDeleting(true)
    
    try {
      // API call
      await apiClient.deleteSession(sessionId)
      
      // Update store
      deleteSession(sessionId)
      
      toast.success('Sessione eliminata con successo')
      onOpenChange(false)
      
    } catch (error) {
      toast.error('Errore durante eliminazione sessione')
      // Non chiudere dialog su errore per permettere retry
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Conferma eliminazione</AlertDialogTitle>
          <AlertDialogDescription>
            Sei sicuro di voler eliminare la sessione "{sessionTitle}"? 
            Questa azione è irreversibile e cancellerà tutti i messaggi associati.
          </AlertDialogDescription>
        </AlertDialogHeader>
        
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Annulla
          </AlertDialogCancel>
          
          <AlertDialogAction
            variant="destructive"
            onClick={(e) => {
              e.preventDefault() // Previeni auto-close
              handleDelete()
            }}
            disabled={isDeleting}
          >
            {isDeleting ? 'Eliminazione...' : 'Elimina'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
```

**Critical Points:**
- `e.preventDefault()` in `AlertDialogAction.onClick` previene auto-close per gestione async
- `disabled={isDeleting}` su entrambi buttons durante API call
- Dialog NON si chiude su error → permette retry utente
- Toast notification per feedback utente

---

### 3.2 Controlled State Pattern

```typescript
// AlertDialog supporta controlled state
const [open, setOpen] = useState(false)

<AlertDialog open={open} onOpenChange={setOpen}>
  {/* content */}
</AlertDialog>

// Usage
<Button onClick={() => setOpen(true)}>Elimina</Button>
<DeleteSessionDialog open={open} onOpenChange={setOpen} />
```

---

### 3.3 Error Handling Options

```typescript
// Opzione 1: Inline error message dentro dialog
const [error, setError] = useState<string | null>(null)

<AlertDialogDescription>
  {error && (
    <div className="text-destructive mb-2">{error}</div>
  )}
  Conferma eliminazione sessione?
</AlertDialogDescription>

// Opzione 2: Toast notification (preferita per Story 9.3)
toast.error('Errore API')
// Dialog rimane aperto per retry
```

---

## 4. Shadcn DropdownMenu

### 4.1 Session Actions Menu con Icons

**File:** `apps/web/src/components/SessionListItem.tsx`

```typescript
import { MoreVertical, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface SessionListItemProps {
  session: SessionMetadata
  onSelect: (id: string) => void
}

export function SessionListItem({ session, onSelect }: SessionListItemProps) {
  const [showRename, setShowRename] = useState(false)
  const [showDelete, setShowDelete] = useState(false)

  return (
    <div className="relative group">
      {/* Session item - click carica sessione */}
      <button
        onClick={() => onSelect(session.id)}
        className="w-full p-3 text-left rounded-lg hover:bg-accent"
      >
        <div className="font-medium pr-8">{session.title}</div>
        <div className="text-sm text-muted-foreground">
          {session.messageCount} messaggi
        </div>
      </button>

      {/* Actions menu - click non propaga */}
      <div 
        className="absolute right-2 top-2"
        onClick={(e) => e.stopPropagation()} // CRITICO: previeni parent click
      >
        <DropdownMenu modal={false}> {/* CRITICO: permetti Dialog nesting */}
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setShowRename(true)}>
              <Pencil className="mr-2 h-4 w-4" />
              Rinomina
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => setShowDelete(true)}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Elimina
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Dialogs */}
      <RenameDialog 
        open={showRename} 
        onOpenChange={setShowRename}
        session={session}
      />
      <DeleteSessionDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        sessionId={session.id}
        sessionTitle={session.title}
      />
    </div>
  )
}
```

**Critical Points:**
- `onClick={(e) => e.stopPropagation()` su menu container previene trigger parent onClick
- `modal={false}` su DropdownMenu permette Dialog nesting senza conflitti
- `opacity-0 group-hover:opacity-100` per show menu on hover (optional UX)
- Icons con `mr-2` per spacing consistente

---

### 4.2 Keyboard Navigation (Auto-gestito)

```typescript
// DropdownMenu auto-gestisce:
// - Arrow Up/Down: navigazione items
// - Enter/Space: select item
// - ESC: chiude menu
// - Tab: esce da menu (chiude)
// - Type-ahead: cerca item per prima lettera
```

**Note:** Non implementare keyboard handlers custom. Shadcn gestisce tutto.

---

## 5. Integration Checklist

### 5.1 Pre-Implementation Setup

```bash
# Step 1: Install Zustand
cd apps/web
pnpm add zustand

# Step 2: Install Shadcn/UI components
npx shadcn@latest add sheet --path apps/web
npx shadcn@latest add dropdown-menu --path apps/web
npx shadcn@latest add alert-dialog --path apps/web

# Step 3: Create store folder
mkdir -p apps/web/src/store

# Step 4: Verify installations
pnpm list zustand
ls -la src/components/ui/{sheet,dropdown-menu,alert-dialog}.tsx
```

---

### 5.2 Implementation Order (Task Sequence)

1. **Task 2:** Zustand store (`sessionStore.ts`) + hydration hook
2. **Task 3:** ChatSidebar responsive component (Sheet + aside)
3. **Task 4:** New Chat button integration
4. **Task 5:** SessionListItem con DropdownMenu
5. **Task 6:** RenameSessionDialog (Dialog, non AlertDialog)
6. **Task 7:** DeleteSessionDialog (AlertDialog)
7. **Task 8:** ChatPage integration
8. **Task 9:** Navigation sandwich icon

**Rule:** Implementare sequenzialmente. Ogni task dipende dal precedente.

---

### 5.3 Verification Points

```typescript
// ✅ Zustand store works
const sessions = useSessionStore.getState().sessions
console.log('Sessions:', sessions)

// ✅ Persist middleware active
console.log('Hydrated:', useSessionStore.persist.hasHydrated())
console.log('localStorage:', localStorage.getItem('chat.sessions'))

// ✅ Sheet responsive behavior
// Test: Resize window sopra/sotto 1024px breakpoint

// ✅ DropdownMenu non propaga click
// Test: Click menu 3 pallini non deve caricare sessione

// ✅ AlertDialog async handling
// Test: Durante delete, buttons disabilitati, dialog non chiude su error
```

---

## 6. Testing Patterns

### 6.1 Zustand Store Unit Tests

**File:** `apps/web/src/store/__tests__/sessionStore.test.ts`

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { useSessionStore } from '../sessionStore'

describe('sessionStore', () => {
  beforeEach(() => {
    useSessionStore.getState().setSessions([])
  })

  it('addSession prepends session to list', () => {
    const newSession = {
      id: '123',
      title: 'Test Session',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messageCount: 0,
    }

    useSessionStore.getState().addSession(newSession)
    
    const sessions = useSessionStore.getState().sessions
    expect(sessions).toHaveLength(1)
    expect(sessions[0]).toEqual(newSession)
  })

  it('deleteSession removes session and clears current if matched', () => {
    const session = { id: '123', title: 'Test', /* ... */ }
    useSessionStore.getState().addSession(session)
    useSessionStore.getState().setCurrentSession('123')

    useSessionStore.getState().deleteSession('123')

    expect(useSessionStore.getState().sessions).toHaveLength(0)
    expect(useSessionStore.getState().currentSessionId).toBeNull()
  })

  it('updateSession modifies existing session', () => {
    const session = { id: '123', title: 'Old', /* ... */ }
    useSessionStore.getState().addSession(session)

    useSessionStore.getState().updateSession('123', { title: 'New' })

    const updated = useSessionStore.getState().sessions[0]
    expect(updated.title).toBe('New')
  })
})
```

---

### 6.2 Component Integration Tests

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DeleteSessionDialog } from '../DeleteSessionDialog'

describe('DeleteSessionDialog', () => {
  it('disables buttons during API call', async () => {
    render(
      <DeleteSessionDialog
        open={true}
        onOpenChange={() => {}}
        sessionId="123"
        sessionTitle="Test"
      />
    )

    const deleteButton = screen.getByText('Elimina')
    fireEvent.click(deleteButton)

    await waitFor(() => {
      expect(deleteButton).toBeDisabled()
      expect(screen.getByText('Annulla')).toBeDisabled()
    })
  })
})
```

---

### 6.3 E2E Playwright Tests

```typescript
test('sidebar mobile overlay: open, select session, auto-close', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 }) // Mobile

  // Click hamburger icon
  await page.click('[aria-label="Menu"]')
  
  // Sheet visible
  await expect(page.locator('[role="dialog"]')).toBeVisible()
  
  // Click session
  await page.click('text=Test Session')
  
  // Sheet auto-closed
  await expect(page.locator('[role="dialog"]')).not.toBeVisible()
})
```

---

## 7. Common Pitfalls

### 7.1 Zustand Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Hydration mismatch** | Store empty on first render | Usa `useHydration()` hook, render loader |
| **Excessive re-renders** | Component re-render su ogni state change | Usa selectors specifici, non destructure |
| **Persist non funziona** | localStorage vuoto | Verifica `partialize` escluda functions |
| **Storage key collision** | Store overwrite altro store | Usa unique `name` prefix (es. `chat.sessions`) |

---

### 7.2 Sheet Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Focus trap non funziona** | ESC key ignorato | Non gestire ESC manualmente, Shadcn lo gestisce |
| **Backdrop click non chiude** | Sheet rimane aperto | Non override `onOpenChange`, usa state controlled |
| **Content non scrolla** | Lista sessioni troncata | Usa `flex-col` + `flex-1 overflow-y-auto` |
| **Body scroll non locked** | Scroll page sotto overlay | Shadcn gestisce automaticamente, non aggiungere CSS |

---

### 7.3 AlertDialog Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Dialog auto-chiude su async** | Dialog chiude prima API complete | `e.preventDefault()` in `AlertDialogAction.onClick` |
| **Buttons non disabilitati** | Doppio click trigger doppio delete | `disabled={isLoading}` su entrambi buttons |
| **Error nascosto** | Utente non vede errore | Non chiudere dialog su error, mostra toast |
| **AlertDialogAction non gestisce async** | Default onClick chiude subito | Override con `onClick={(e) => { e.preventDefault(); handleAsync() }}` |

---

### 7.4 DropdownMenu Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Click propaga a parent** | Menu click carica sessione | `e.stopPropagation()` su menu container |
| **Dialog non si apre da menu** | Dialog blocked da dropdown | `modal={false}` su DropdownMenu |
| **Icons disallineati** | Icons + text non spacing corretto | `mr-2` su icon component |
| **Z-index conflict** | Menu sotto altro overlay | Verifica z-index (default 50), adjust se necessario |

---

## Version References

- **Zustand:** v4.5.0+ (stable 2024-2025, persist middleware integrato)
- **Shadcn/UI:** Components aggiornati Q4 2024, basati su Radix UI Primitives
- **React:** 19.x compatible (tutti patterns)
- **TypeScript:** 5.x required per type inference corretta
- **Tailwind CSS:** 4.x (breakpoints `lg:` = 1024px)

---

## References

- **Story 9.3:** `docs/stories/9.3-chat-session-management-ui.md`
- **Tech Stack:** `docs/architecture/sezione-3-tech-stack.md` L7-8
- **Testing Strategy:** `docs/architecture/sezione-11-strategia-di-testing.md`
- **Shadcn Components Registry:** `docs/architecture/addendum-shadcn-components-registry.md`
- **Story 9.2 Pattern:** Session history retrieval (baseline implementation)

---

## Implementation Support

Per domande o problemi durante implementazione:
1. Verificare Integration Checklist (Section 5)
2. Consultare Common Pitfalls (Section 7)
3. Riferimento Story 9.2 per pattern simili già implementati
4. Test pattern validation prima di procedere con task successivo

