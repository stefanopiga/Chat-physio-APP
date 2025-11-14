# Virtual Scrolling - Librerie React

## Comparazione Librerie

| Libreria | Bundle Size | TypeScript | Framework |
|----------|-------------|------------|-----------|
| react-window | ~7kb | ✓ | React |
| @tanstack/virtual | ~10-15kb | ✓ | React, Vue, Solid, Svelte, Angular |
| react-virtuoso | ~15kb | ✓ | React |

## TanStack Virtual

**Caratteristiche:**
- Headless UI (controllo completo su markup e stili)
- Supporto vertical, horizontal, grid layouts
- Window scrolling
- Sizing: fisso, variabile, dinamico
- Sticky items
- Framework agnostic

**Installazione:**
```bash
npm install @tanstack/react-virtual
```

**Esempio base:**
```typescript
import { useVirtualizer } from '@tanstack/react-virtual'

const rowVirtualizer = useVirtualizer({
  count: 1000,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 36,
})

// Map virtual rows to UI
```

**Bundle:** 10-15kb tree-shakeable

**Download NPM:** 344M+ mensili

**Repository:** https://tanstack.com/virtual/latest

---

## react-window

**Caratteristiche:**
- Rendering ottimizzato per liste molto lunghe
- API semplificata
- Supporto liste fisse e variabili

**Repository:** https://react-window.vercel.app/

---

## react-virtuoso

**Caratteristiche:**
- Gestione automatica altezze variabili
- Responsive layout
- GroupedVirtuoso per liste con headers sticky
- TableVirtuoso per tabelle
- VirtuosoGrid per griglie responsive
- MessageList per chat interfaces
- Masonry per gallery

**Installazione:**
```bash
npm install react-virtuoso
```

**Esempio Virtuoso:**
```typescript
<Virtuoso
  style={{ height: '400px' }}
  totalCount={1000}
  itemContent={(index) => <div>Item {index}</div>}
/>
```

**Esempio GroupedVirtuoso:**
```typescript
<GroupedVirtuoso
  groupCounts={[20, 30]}
  groupContent={(index) => <div>Group {index}</div>}
  itemContent={(index, groupIndex) => (
    <div>Item {index} in group {groupIndex}</div>
  )}
/>
```

**Performance:**
- Usa React.memo per contenuti item complessi
- increaseViewportBy per controllo rendering extra
- isScrolling callback per gestione scroll

**Repository:** https://virtuoso.dev/

---

## Raccomandazioni

**TanStack Virtual** se:
- Serve massimo controllo UI
- Progetti multi-framework
- Necessità di tree-shaking aggressivo

**react-virtuoso** se:
- Altezze variabili automatiche
- Tabelle, chat, masonry
- API di alto livello preferita

**react-window** se:
- Bundle size critico
- Liste semplici con sizing fisso
