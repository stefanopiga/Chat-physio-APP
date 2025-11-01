# Addendum: Shadcn/UI Components Registry

**Date**: 2025-10-05  
**Scope**: Tracking installazioni componenti Shadcn/UI per story  
**Type**: Reference Documentation

---

## Document Purpose

Registro completo componenti Shadcn/UI installati nel progetto, tracciati per story di implementazione. Fornisce quick reference per:
- Verificare disponibilità componenti
- Identificare story che hanno introdotto componente
- Validare installazioni pre-implementation

---

## Components Registry

### Componenti Attivi

| Component | File | Story | Installation Date | Command |
|-----------|------|-------|-------------------|---------|
| Card | `apps/web/src/components/ui/card.tsx` | 4.1.5 | 2025-10-01 | `pnpm dlx shadcn@latest add card` |
| Dialog | `apps/web/src/components/ui/dialog.tsx` | Pre-4.1 | - | `pnpm dlx shadcn@latest add dialog` |
| Select | `apps/web/src/components/ui/select.tsx` | 4.4 | 2025-10-05 | `pnpm dlx shadcn@latest add select` |
| Badge | `apps/web/src/components/ui/badge.tsx` | 4.4 | 2025-10-05 | `pnpm dlx shadcn@latest add badge` |
| Button | `apps/web/src/components/ui/button.tsx` | 4.4 | 2025-10-05 | `pnpm dlx shadcn@latest add button` |

**Total Components**: 5

---

## Component Usage Matrix

### Card Component

**Installed**: Story 4.1.5  
**Used By**:
- Story 4.1.5 (Admin Dashboard Hub) - Container navigation cards
- Story 4.2 (Analytics Dashboard) - Metrics cards
- Story 4.4 (Document Chunk Explorer) - Document table container, chunk cards

**Exports**:
- `Card` - Container principale
- `CardHeader` - Header con title/description
- `CardTitle` - Titolo card
- `CardDescription` - Descrizione card
- `CardContent` - Contenuto principale
- `CardFooter` - Footer azioni

**References**:
- `docs/architecture/addendum-implementation-guide-4.1.5.md`
- `docs/stories/4.1.5-admin-dashboard-hub.md`

---

### Dialog Component

**Installed**: Pre-Story 4.1 (data esatta non tracciata)  
**Used By**:
- `src/components/HelpModal.tsx` - Modal aiuto contestuale
- Story 4.4 (Document Chunk Explorer) - Full content chunk viewer

**Exports**:
- `Dialog` - Root component
- `DialogTrigger` - Elemento che attiva apertura
- `DialogContent` - Finestra modale
- `DialogHeader` - Header strutturato
- `DialogTitle` - Titolo modal
- `DialogDescription` - Descrizione modal
- `DialogFooter` - Footer azioni

**References**:
- `docs/architecture/addendum-shadcn-dialog-implementation.md`
- `src/components/HelpModal.tsx` (pattern reference)

---

### Select Component

**Installed**: Story 4.4  
**Used By**:
- Story 4.4 (Document Chunk Explorer) - Filtri dropdown strategia chunking e ordinamento

**Exports**:
- `Select` - Root component
- `SelectTrigger` - Bottone apertura dropdown
- `SelectValue` - Placeholder o valore selezionato
- `SelectContent` - Container opzioni
- `SelectItem` - Singola opzione selezionabile
- `SelectGroup` - Raggruppamento opzioni
- `SelectLabel` - Label gruppo

**Usage Pattern** (Story 4.4):
```tsx
<Select onValueChange={handleStrategyFilter}>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Strategy" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="all">All</SelectItem>
    <SelectItem value="recursive">Recursive</SelectItem>
    <SelectItem value="semantic">Semantic</SelectItem>
  </SelectContent>
</Select>
```

**References**:
- `docs/stories/4.4-document-chunk-explorer.md` (L332-344, L405-456)

---

### Badge Component

**Installed**: Story 4.4  
**Used By**:
- Story 4.4 (Document Chunk Explorer) - Status indicator chunking strategy ed embedding status

**Exports**:
- `Badge` - Component principale con variants

**Variants**:
- `default` - Badge standard (grigio)
- `secondary` - Badge secondario
- `destructive` - Badge errore (rosso)
- `outline` - Badge con bordo

**Usage Pattern** (Story 4.4):
```tsx
<Badge variant={chunk.embedding_status === 'indexed' ? 'default' : 'secondary'}>
  {chunk.embedding_status}
</Badge>
```

**References**:
- `docs/stories/4.4-document-chunk-explorer.md`
- Test: `apps/web/src/pages/__tests__/DocumentsPage.test.tsx` (Test 6)

---

### Button Component

**Installed**: Story 4.4  
**Used By**:
- Story 4.4 (Document Chunk Explorer) - Navigazione documenti/chunk, trigger dialog

**Exports**:
- `Button` - Component principale con variants

**Variants**:
- `default` - Button primario
- `destructive` - Button azione distruttiva
- `outline` - Button con bordo
- `secondary` - Button secondario
- `ghost` - Button trasparente
- `link` - Button stile link

**Sizes**:
- `default` - Dimensione standard
- `sm` - Small
- `lg` - Large
- `icon` - Solo icona

**Usage Pattern** (Story 4.4):
```tsx
<Button size="sm">Visualizza Chunk</Button>
<Button variant="link" size="sm">Mostra contenuto completo</Button>
```

**References**:
- `docs/stories/4.4-document-chunk-explorer.md`

---

## Installation Procedure

### Standard Installation

```bash
cd apps/web
pnpm dlx shadcn@latest add <component-name>
```

### Verification Post-Installation

```bash
# Verificare file creato
ls -la src/components/ui/<component-name>.tsx

# Verificare exports disponibili
grep "export" src/components/ui/<component-name>.tsx
```

---

## Setup Requirements

**Prerequisites** (già configurato):
- ✅ Tailwind CSS (`@tailwindcss/vite`)
- ✅ Shadcn/UI init (`components.json`)
- ✅ TypeScript path alias (`@/*` → `./src/*`)
- ✅ Vite config con alias resolution

**References**:
- Setup base: `docs/architecture/addendum-tailwind-shadcn-setup.md`

---

## Component Planning Matrix

| Story | Componenti Richiesti | Status | Notes |
|-------|---------------------|--------|-------|
| 4.1.5 | Card | ✅ Installato | Dashboard hub container |
| 4.2 | Card (riuso) | ✅ Disponibile | Analytics metrics cards |
| 4.4 | Select, Badge, Button | ✅ Installati | Document explorer filters/status |
| Future | Table, Input, Form | ⏳ Pending | Per future features |

---

## Troubleshooting

### Component Import Error

**Symptom**: `Cannot find module '@/components/ui/card'`

**Solution**:
1. Verificare file esiste: `ls apps/web/src/components/ui/card.tsx`
2. Se mancante, installare: `pnpm dlx shadcn@latest add card`
3. Verificare `tsconfig.json` ha path alias configurato

### TypeScript Compilation Error

**Symptom**: `Property 'variant' does not exist on type...`

**Solution**:
1. Reinstallare componente: `pnpm dlx shadcn@latest add <component>`
2. Riavviare TypeScript server
3. Verificare versione Shadcn CLI: `pnpm dlx shadcn@latest --version`

---

## References

### Documentation
- Shadcn/UI Official: https://ui.shadcn.com/docs/components
- Setup Guide: `docs/architecture/addendum-tailwind-shadcn-setup.md`
- Dialog Implementation: `docs/architecture/addendum-shadcn-dialog-implementation.md`

### Stories
- Story 4.1.5: `docs/stories/4.1.5-admin-dashboard-hub.md` (Card)
- Story 4.4: `docs/stories/4.4-document-chunk-explorer.md` (Select, Badge, Button)

### Implementation Guides
- Card: `docs/architecture/addendum-implementation-guide-4.1.5.md`
- Dialog: `docs/architecture/addendum-shadcn-dialog-implementation.md`

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2025-10-05 | AI | Initial registry creation. Documented 5 components (Card, Dialog, Select, Badge, Button) con tracking per story e usage patterns. |

---

**Status**: ✅ Active Reference  
**Maintenance**: Aggiornare registro ad ogni installazione nuovo componente Shadcn/UI  
**Owner**: Development Team

