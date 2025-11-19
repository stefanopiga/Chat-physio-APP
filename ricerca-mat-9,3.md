[8 tools called]

## DOCUMENTO 1: Zustand v4 Store con Persist Middleware

### Pattern Store Base con TypeScript

```typescript
// apps/web/src/stores/sessionStore.ts
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
      name: 'chat.sessions',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
)
```

### Hydration Pattern per SSR/Next.js

```typescript
// apps/web/src/components/SessionHydration.tsx
import { useEffect, useState } from 'react'
import { useSessionStore } from '@/stores/sessionStore'

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

// Usage in component
function SessionList() {
  const hydrated = useHydration()
  const sessions = useSessionStore((state) => state.sessions)

  if (!hydrated) {
    return <div>Loading sessions...</div>
  }

  return <div>{/* render sessions */}</div>
}
```

### Performance: Selectors Optimization

```typescript
// BAD - Re-render su ogni store change
const { sessions, addSession } = useSessionStore()

// GOOD - Re-render solo quando sessions cambia
const sessions = useSessionStore((state) => state.sessions)
const addSession = useSessionStore((state) => state.addSession)

// BEST - Con shallow equality per array/objects
import { shallow } from 'zustand/shallow'

const [sessions, addSession] = useSessionStore(
  (state) => [state.sessions, state.addSession],
  shallow
)
```

### API Methods Disponibili

```typescript
// Clear storage
useSessionStore.persist.clearStorage()

// Manual rehydrate
await useSessionStore.persist.rehydrate()

// Check hydration status (non-reactive)
const isHydrated = useSessionStore.persist.hasHydrated()

// Outside React: getState()
const currentSessions = useSessionStore.getState().sessions
useSessionStore.getState().addSession(newSession)
```

### Pitfalls Comuni

1. **Hydration mismatch in SSR**: Store non idratato a initial render. Usa `useHydration()` hook.
2. **Performance**: Evita destructuring completo dello state. Usa selectors specifici.
3. **Persist partialize**: Ometti functions/non-serializable data. Solo plain objects.
4. **Storage key collision**: `name` deve essere unique per app. Usa namespace prefix.

---

## DOCUMENTO 2: Shadcn Sheet Component

### Pattern Sidebar Responsive (Mobile Sheet + Desktop Aside)

```typescript
// apps/web/src/components/ChatSidebar.tsx
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
import { useSessionStore } from '@/stores/sessionStore'

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
        <h2 className="text-lg font-semibold">Chat Sessions</h2>
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
              {session.messageCount} messages
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
            <SheetTitle>Chat Sessions</SheetTitle>
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

### Sheet Side Configuration

```typescript
// Left sidebar (default per nav)
<SheetContent side="left">

// Right panel (per settings/filters)
<SheetContent side="right">

// Top/Bottom (mobile drawer alternative)
<SheetContent side="bottom">
```

### Scroll Behavior con Lista Lunga

```typescript
<SheetContent side="left" className="p-0 flex flex-col">
  {/* Fixed header */}
  <div className="p-4 border-b">
    <h2>Sessions</h2>
  </div>
  
  {/* Scrollable content */}
  <div className="flex-1 overflow-y-auto p-4">
    {sessions.map((s) => (
      <SessionItem key={s.id} session={s} />
    ))}
  </div>
  
  {/* Fixed footer (optional) */}
  <div className="p-4 border-t">
    <Button>New Session</Button>
  </div>
</SheetContent>
```

### Z-Index Management

```typescript
// Sheet default z-index: 50 (overlay), 51 (content)
// AlertDialog z-index: 52 (garantito sopra Sheet)

// Se conflitti custom:
<SheetContent className="z-[100]">
```

### Pitfalls Comuni

1. **Focus trap**: ESC key chiude Sheet automaticamente. Non gestire ESC manualmente.
2. **Backdrop click**: Click outside chiude Sheet. Se serve prevenire, usa `onOpenChange` validation.
3. **Navigation sync**: `setOpen(false)` dopo navigation per UX mobile corretta.
4. **Scroll lock body**: Shadcn gestisce automaticamente. Non aggiungere `overflow-hidden` manuale.

---

## DOCUMENTO 3: Shadcn AlertDialog

### Pattern Delete Confirmation con Async API

```typescript
// apps/web/src/components/DeleteSessionDialog.tsx
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
import { useSessionStore } from '@/stores/sessionStore'
import { toast } from 'sonner'

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
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
      
      // Update store
      deleteSession(sessionId)
      
      toast.success('Sessione eliminata')
      onOpenChange(false)
      
    } catch (error) {
      toast.error('Errore durante eliminazione')
      // Non chiudere dialog su errore
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
            Stai per eliminare la sessione "{sessionTitle}". 
            Questa azione non può essere annullata.
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

// Usage
function SessionListItem({ session }) {
  const [showDelete, setShowDelete] = useState(false)
  
  return (
    <>
      <button onClick={() => setShowDelete(true)}>
        Elimina
      </button>
      
      <DeleteSessionDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        sessionId={session.id}
        sessionTitle={session.title}
      />
    </>
  )
}
```

### Controlled State Pattern

```typescript
// AlertDialog supporta controlled state
const [open, setOpen] = useState(false)

<AlertDialog open={open} onOpenChange={setOpen}>
  {/* content */}
</AlertDialog>
```

### Error Handling Inside AlertDialog

```typescript
// Opzione 1: Inline error message
const [error, setError] = useState<string | null>(null)

<AlertDialogDescription>
  {error && (
    <div className="text-destructive mb-2">{error}</div>
  )}
  Conferma eliminazione sessione?
</AlertDialogDescription>

// Opzione 2: Toast notification (preferita)
toast.error('Errore API')
// Dialog rimane aperto per retry
```

### Accessibility

```typescript
// AlertDialog auto-gestisce:
// - aria-labelledby (AlertDialogTitle)
// - aria-describedby (AlertDialogDescription)
// - role="alertdialog"
// - Focus trap automatico
// - ESC key close (se non disabled)

// Screen reader announce: automatico via role
```

### Pitfalls Comuni

1. **Async actions**: `e.preventDefault()` in `AlertDialogAction.onClick` per gestione async manuale.
2. **Auto-close prevention**: Disabilita buttons durante API call con `disabled={isLoading}`.
3. **Error state**: Non chiudere dialog su error. Permetti retry.
4. **AlertDialogAction default**: Ha `onClick` che chiude automaticamente. Override con `preventDefault()` per async.

---

## DOCUMENTO 4: Shadcn DropdownMenu

### Pattern Session Actions Menu con Icons

```typescript
// apps/web/src/components/SessionListItem.tsx
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
          {session.messageCount} messages
        </div>
      </button>

      {/* Actions menu - click non propaga */}
      <div 
        className="absolute right-2 top-2"
        onClick={(e) => e.stopPropagation()} // Previeni parent click
      >
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              className="h-8 w-8"
            >
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => setShowRename(true)}
            >
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
      <DeleteDialog
        open={showDelete}
        onOpenChange={setShowDelete}
        session={session}
      />
    </div>
  )
}
```

### Keyboard Navigation

```typescript
// DropdownMenu auto-gestisce:
// - Arrow Up/Down: navigazione items
// - Enter/Space: select item
// - ESC: chiude menu
// - Tab: esce da menu (chiude)
// - Type-ahead: cerca item per prima lettera
```

### Programmatic Close

```typescript
// Opzione 1: State controlled
const [open, setOpen] = useState(false)

<DropdownMenu open={open} onOpenChange={setOpen}>
  <DropdownMenuContent>
    <DropdownMenuItem onClick={() => {
      doAction()
      setOpen(false) // Chiusura manuale
    }}>
      Action
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>

// Opzione 2: Default behavior
// DropdownMenuItem auto-chiude on click (default)
<DropdownMenuItem onClick={doAction}>
  {/* Chiude automaticamente */}
</DropdownMenuItem>
```

### Integration con Dialog (Modal Issue)

```typescript
// CRITICO: Dialog dentro DropdownMenu richiede modal={false}
<DropdownMenu modal={false}>
  <DropdownMenuContent>
    <DropdownMenuItem onSelect={() => setShowDialog(true)}>
      Open Dialog
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>

<Dialog open={showDialog} onOpenChange={setShowDialog}>
  {/* Dialog content */}
</Dialog>
```

### Mobile Touch Behavior

```typescript
// DropdownMenu auto-gestisce:
// - Touch outside: chiude menu
// - Touch item: select + close
// - Scroll: permesso se content overflow

// Touch target size: garantito 44x44px minimum
<DropdownMenuTrigger asChild>
  <Button size="icon-sm" className="h-10 w-10"> {/* Min 40px */}
    <MoreVertical />
  </Button>
</DropdownMenuTrigger>
```

### Pitfalls Comuni

1. **Click propagation**: `e.stopPropagation()` su container menu per evitare trigger parent onClick.
2. **Dialog conflict**: Usa `modal={false}` su DropdownMenu se apri Dialog da MenuItem.
3. **Icons alignment**: Usa `mr-2` su icon + text in DropdownMenuItem per spacing consistente.
4. **Z-index**: DropdownMenuContent ha z-50 default. Verificare con altri overlays.

---

## VERSION REFERENCES

- **Zustand**: v4.5.0+ (stable 2024-2025, persist middleware integrato)
- **Shadcn/UI**: Components aggiornati Q4 2024, basati su Radix UI Primitives
- **React**: 19.x compatible (tutti patterns)
- **TypeScript**: 5.x required per type inference corretta

## INTEGRATION CHECKLIST

1. Zustand store: verificare `name` key unique
2. Sheet: testare mobile/desktop breakpoint `lg:`
3. AlertDialog: implementare loading state per async
4. DropdownMenu: aggiungere `modal={false}` se nested dialogs