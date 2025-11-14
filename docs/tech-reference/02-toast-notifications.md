# Toast Notifications

## Sonner (Raccomandato shadcn/ui)

**Caratteristiche:**
- Opinionated toast component
- API semplice
- Swipe direction basato su posizione
- Rich colors support
- Expand/collapse control

**Installazione:**
```bash
npm install sonner
```

**Setup base:**
```typescript
import { Toaster, toast } from 'sonner'

function App() {
  return (
    <div>
      <Toaster />
      <button onClick={() => toast('My first toast')}>
        Give me a toast
      </button>
    </div>
  )
}
```

**Tipi:**
```typescript
toast('Event has been created')
toast.success('Event has been created')
toast.error('Something went wrong')
toast.warning('Be careful')
toast.info('Did you know?')
```

**Position:**
```typescript
<Toaster position="bottom-right" />
// Opzioni: top-left, top-center, top-right, 
//          bottom-left, bottom-center, bottom-right
```

**Expand control:**
```typescript
<Toaster expand={false} />
// Controlla quanti toast visibili via visibleToasts prop
```

**Rich colors:**
```typescript
<Toaster richColors />
```

**Repository:** https://sonner.emilkowal.ski/

---

## shadcn/ui Toast

**Stato:** Deprecato in favore di Sonner

**Installazione (legacy):**
```bash
npx shadcn-ui@latest add toast
```

**Nota:** Documentazione ufficiale raccomanda migrazione a Sonner.

**Repository:** https://ui.shadcn.com/docs/components/toast

---

## Raccomandazioni

**Usa Sonner:**
- Raccomandazione ufficiale shadcn/ui
- API moderna e semplice
- Manutenzione attiva
- Migliore UX out-of-the-box
