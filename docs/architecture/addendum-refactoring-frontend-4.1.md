# Addendum: Refactoring Frontend per Story 4.1 - Admin Debug View

**Data:** 2025-10-01  
**Autore:** QA Lead / Scrum Master  
**Scope:** Refactoring strutturale componenti UI Story 4.1

---

## Contesto

Durante l'implementazione della Story 4.1 (Admin Debug View), i componenti UI sono stati implementati "inline" all'interno del file `AdminDebugPage.tsx`. Sebbene funzionale, questo approccio presenta limitazioni architetturali:

- **Manutenibilità ridotta**: Logica di presentazione mescolata con logica di orchestrazione della pagina
- **Riusabilità zero**: Componenti non estraibili per altri contesti
- **Disallineamento architetturale**: Deviazione dalla struttura modulare del progetto (confronta `ChatInput.tsx`, `ChatMessagesList.tsx`, `CitationBadge.tsx`)

**Obiettivo del refactoring:** Estrarre i componenti inline in file dedicati, mantenendo invariata la funzionalità e l'aspetto visivo.

---

## Componenti da Creare

### 1. `DebugQueryForm.tsx`

**Percorso:** `apps/web/src/components/DebugQueryForm.tsx`

**Responsabilità:**
- Gestire il form per l'invio della domanda di debug
- Validazione client-side (domanda non vuota)
- Gestione stato di loading e disabilitazione controlli
- Accessibilità: label esplicite, focus visibile

**Props TypeScript:**
```typescript
interface DebugQueryFormProps {
  onSubmit: (question: string) => Promise<void>;
  isLoading: boolean;
}
```

**Estratto da `AdminDebugPage.tsx`:**
- Righe 69-87 (form con textarea e button)
- Stati gestiti: `question` (locale al form)
- Evento submit: invoca `props.onSubmit(question.trim())`

**Note implementative:**
- Mantenere classi Tailwind esistenti per preservare theming
- Aria-label su textarea per screen reader
- Disabilitare submit se `isLoading || !question.trim()`

---

### 2. `ChunkList.tsx`

**Percorso:** `apps/web/src/components/ChunkList.tsx`

**Responsabilità:**
- Renderizzare la lista di chunk recuperati
- Gestire empty state (nessun chunk disponibile)
- Layout responsive (grid 1 col → 2 col su md+)

**Props TypeScript:**
```typescript
type DebugChunk = {
  chunk_id: string | null;
  content: string | null;
  similarity_score: number | null;
  metadata: {
    document_id?: string | null;
    document_name?: string | null;
    page_number?: number | null;
    chunking_strategy?: string | null;
  } | null;
};

interface ChunkListProps {
  chunks: DebugChunk[];
}
```

**Estratto da `AdminDebugPage.tsx`:**
- Righe 107-155 (sezione "Chunk Recuperati" completa)
- Rendering condizionale empty state (righe 111-115)
- Grid con mapping su `chunks` array

**Note implementative:**
- Importare tipo `DebugChunk` da file shared o ridefinire localmente
- Passare ogni chunk al componente `ChunkCard`
- Preservare key pattern: `${c.chunk_id ?? "unknown"}-${idx}`

---

### 3. `ChunkCard.tsx`

**Percorso:** `apps/web/src/components/ChunkCard.tsx`

**Responsabilità:**
- Visualizzare dettagli di un singolo chunk
- Mostrare score di similarità con badge
- Metadati collassabili in `<details>`
- Preview contenuto (primi 200 caratteri)

**Props TypeScript:**
```typescript
type DebugChunk = {
  chunk_id: string | null;
  content: string | null;
  similarity_score: number | null;
  metadata: {
    document_id?: string | null;
    document_name?: string | null;
    page_number?: number | null;
    chunking_strategy?: string | null;
  } | null;
};

interface ChunkCardProps {
  chunk: DebugChunk;
}
```

**Estratto da `AdminDebugPage.tsx`:**
- Righe 117-153 (singola card nel mapping)
- Header con document_name/chunk_id + badge score
- Content preview con ellipsis se > 200 caratteri
- Details per metadati (document_id, page_number, chunking_strategy)

**Note implementative:**
- Preservare tutte le classi Tailwind per theming semantico
- Formattazione score: `.toFixed(3)` se `typeof === "number"`, altrimenti "N/A"
- Fallback titolo: `metadata?.document_name || metadata?.document_id || chunk_id || "Chunk"`

---

## Refactoring Steps

### Step 1: Creare i nuovi file componenti
1. Creare `apps/web/src/components/DebugQueryForm.tsx`
2. Creare `apps/web/src/components/ChunkList.tsx`
3. Creare `apps/web/src/components/ChunkCard.tsx`

### Step 2: Estrarre la logica
- Copiare il JSX corrispondente da `AdminDebugPage.tsx`
- Tipizzare le props come specificato
- Sostituire riferimenti a stati locali con `props`

### Step 3: Aggiornare `AdminDebugPage.tsx`
- Importare i nuovi componenti
- Sostituire i blocchi JSX inline con componenti
- Mantenere la logica di orchestrazione (stato `data`, `error`, `loading`, chiamata API)

### Step 4: Test di non-regressione
- Eseguire test E2E esistenti (`apps/web/tests/story-4.1.spec.ts`)
- Verificare rendering identico in Light/Dark mode
- Confermare accessibilità keyboard navigation

---

## Esempio di Refactoring `AdminDebugPage.tsx`

**Prima (inline):**
```tsx
<form onSubmit={onSubmit} className="space-y-3">
  <label htmlFor="question" ...>Domanda di test</label>
  <textarea id="question" ... />
  <button type="submit" ...>Esegui Query Debug</button>
</form>
```

**Dopo (componente estratto):**
```tsx
<DebugQueryForm
  onSubmit={async (q) => {
    setError(null);
    setData(null);
    setLoading(true);
    try {
      const res = await apiClient.adminDebugQuery(q);
      setData(res);
    } catch (err) { /* ... */ }
    finally { setLoading(false); }
  }}
  isLoading={loading}
/>
```

---

## Validazione Architetturale

Dopo il refactoring, verificare che:
- [x] I file `DebugQueryForm.tsx`, `ChunkList.tsx`, `ChunkCard.tsx` esistono in `apps/web/src/components/`
- [x] `AdminDebugPage.tsx` importa e utilizza i nuovi componenti
- [ ] Nessuna funzionalità o stile è stato alterato (test E2E verdi) — Test E2E da completare dopo risoluzione mocking Supabase
- [x] La documentazione in `docs/stories/4.1.admin-debug-view.md` riflette la nuova struttura

**Status:** Refactoring completato il 2025-10-01. Test E2E in attesa di risoluzione problema mocking Supabase auth.

---

## Riferimenti

- Pattern esistenti: `apps/web/src/components/ChatInput.tsx`, `ChatMessagesList.tsx`
- Story 4.1: `docs/stories/4.1.admin-debug-view.md`
- Architettura generale: `docs/architecture/index.md` - Sezione Frontend Structure

