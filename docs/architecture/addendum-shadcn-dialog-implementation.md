# Addendum — Implementazione Dialog Shadcn/UI

Riferimento tecnico per implementazione di modali accessibili con Shadcn/UI Dialog component. Guida operativa per Story 3.5 (In-App User Guide) e implementazioni future di dialog/modal.

[Fonti: Shadcn/UI Dialog documentation; Radix UI Primitives; Story 3.5 requirements]

---

## 1. Implementazione Base del Dialog

Il componente `Dialog` di Shadcn/UI si basa su Radix UI e fornisce accessibilità nativa conforme a WAI-ARIA.

### Struttura Base

```tsx
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { HelpCircle, X } from "lucide-react";

export function HelpModal() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Apri guida"
        >
          <HelpCircle className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Guida all'uso di FisioRAG</DialogTitle>
          <DialogDescription>
            Scopri come utilizzare la chat per ottenere il massimo dalle tue domande.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {/* Contenuto guida */}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

### Caratteristiche Tecniche

- **Portal Rendering**: `Dialog` monta automaticamente il contenuto in un portal al root del DOM, evitando problemi di z-index con container parent.
- **`asChild` Pattern**: `DialogTrigger asChild` trasferisce il comportamento di trigger al componente figlio (Button), preservandone le caratteristiche native.
- **Mounting/Unmounting**: il componente gestisce automaticamente il ciclo di vita del dialog nel DOM; nessuna logica di stato aggiuntiva richiesta per mount/unmount.

[Fonte: `docs/stories/3.5.in-app-user-guide.md` L67]

---

## 2. Styling con Tailwind CSS

Personalizzazione del Dialog con utility classes Tailwind, rispettando variabili semantiche per theming.

### Dialog Content Styling

```tsx
<DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
  <DialogHeader className="relative">
    <DialogTitle className="text-2xl font-semibold pr-8">
      Guida all'uso di FisioRAG
    </DialogTitle>
    <DialogDescription className="text-muted-foreground">
      Scopri come utilizzare la chat per ottenere il massimo dalle tue domande.
    </DialogDescription>
    <DialogClose className="absolute right-0 top-0 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground">
      <X className="h-4 w-4" />
      <span className="sr-only">Chiudi</span>
    </DialogClose>
  </DialogHeader>
  <div className="space-y-6 py-4">
    {/* Contenuto guida */}
  </div>
</DialogContent>
```

### Utility Classes Chiave

| Class | Scopo |
|-------|-------|
| `sm:max-w-[600px]` | Larghezza massima responsive (600px su schermi ≥640px) |
| `max-h-[80vh]` | Altezza massima 80% viewport height |
| `overflow-y-auto` | Scroll verticale per contenuti lunghi |
| `absolute right-0 top-0` | Posizionamento pulsante chiusura in alto a destra |
| `sr-only` | Testo visibile solo a screen reader (accessibilità) |
| `ring-offset-background` | Offset anello focus rispetto a sfondo (migliora contrasto) |
| `data-[state=open]:bg-accent` | Styling condizionale basato su stato data-attribute |

[Fonte: `docs/prompt-for-lovable_V0.md` L50, L59]

---

## 3. Gestione dell'Accessibilità

Il Dialog Shadcn/UI implementa nativamente gli standard WAI-ARIA per dialoghi modali.

### Attributi ARIA Automatici

```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button
      variant="ghost"
      size="icon"
      aria-label="Apri guida"
    >
      <HelpCircle className="h-5 w-5" />
    </Button>
  </DialogTrigger>
  <DialogContent>
    {/* 
      Attributi ARIA gestiti automaticamente dal componente:
      - role="dialog"
      - aria-labelledby → riferimento al DialogTitle
      - aria-describedby → riferimento al DialogDescription
      - aria-modal="true"
    */}
    <DialogHeader>
      <DialogTitle id="help-modal-title">
        Guida all'uso di FisioRAG
      </DialogTitle>
      <DialogDescription id="help-modal-desc">
        Scopri come utilizzare la chat per ottenere il massimo dalle tue domande.
      </DialogDescription>
    </DialogHeader>
    {/* Contenuto */}
    <DialogClose asChild>
      <Button variant="outline">
        Chiudi
      </Button>
    </DialogClose>
  </DialogContent>
</Dialog>
```

### Caratteristiche di Accessibilità Implementate

1. **Focus Trap**: il focus rimane confinato all'interno del dialog durante l'apertura; navigazione con `Tab`/`Shift+Tab` cicla solo tra elementi interni.
2. **Chiusura con `Esc`**: gestita automaticamente dal componente; focus ritorna al trigger dopo chiusura.
3. **Chiusura con Click su Overlay**: click sull'area backdrop chiude il dialog.
4. **Ripristino Focus**: dopo la chiusura, il focus ritorna automaticamente all'elemento trigger.
5. **`aria-label`**: obbligatorio per il pulsante trigger quando usa solo icona (nessun testo visibile).
6. **`aria-labelledby`/`aria-describedby`**: collegamento semantico tra dialog e suoi descrittori (Title/Description).

### Requisiti WCAG AA Conformità

- **Contrasto colori**: variabili semantiche garantiscono contrasto minimo 4.5:1 (testo normale) e 3:1 (testo grande).
- **Navigazione tastiera**: tutti i controlli interattivi raggiungibili con `Tab`.
- **Focus visibile**: anello di focus su tutti gli elementi interattivi (gestito da `focus:ring-2`).
- **Screen reader**: ruoli e label semantici annunciati correttamente.

[Fonti: `docs/front-end-spec.md` Sez. 7 L227–L243; `docs/stories/3.5.in-app-user-guide.md` L23, L44]

---

## 4. Implementazione del Theming Light/Dark

Utilizzo delle variabili di colore semantiche di Tailwind CSS per supporto automatico dei temi Light/Dark.

### Esempio Completo con Theming

```tsx
<Dialog>
  <DialogTrigger asChild>
    <Button
      variant="ghost"
      size="icon"
      aria-label="Apri guida"
      className="text-foreground hover:bg-accent hover:text-accent-foreground"
    >
      <HelpCircle className="h-5 w-5" />
    </Button>
  </DialogTrigger>
  <DialogContent className="bg-background text-foreground border-border">
    <DialogHeader>
      <DialogTitle className="text-foreground">
        Guida all'uso di FisioRAG
      </DialogTitle>
      <DialogDescription className="text-muted-foreground">
        Scopri come utilizzare la chat.
      </DialogDescription>
    </DialogHeader>
    <div className="space-y-4 py-4">
      <section className="rounded-lg border border-border bg-card p-4 text-card-foreground">
        <h3 className="font-semibold text-lg mb-2">Come porre domande</h3>
        <p className="text-sm text-muted-foreground">
          Inserisci la tua domanda e premi Invio...
        </p>
      </section>
    </div>
    <DialogClose asChild>
      <Button variant="outline" className="border-border text-foreground hover:bg-accent">
        Chiudi
      </Button>
    </DialogClose>
  </DialogContent>
</Dialog>
```

### Variabili Semantiche Utilizzate

| Variabile CSS | Tailwind Class | Scopo |
|---------------|----------------|-------|
| `--background` | `bg-background` | Sfondo principale applicazione |
| `--foreground` | `text-foreground` | Testo principale |
| `--card` | `bg-card` | Sfondo sezioni contenuto |
| `--card-foreground` | `text-card-foreground` | Testo su sfondo card |
| `--muted-foreground` | `text-muted-foreground` | Testo secondario/descrittivo |
| `--border` | `border-border` | Bordi |
| `--accent` | `bg-accent` | Stati hover/focus |
| `--accent-foreground` | `text-accent-foreground` | Testo su sfondo accent |
| `--popover` | `bg-popover` | Sfondo overlay dialog |
| `--popover-foreground` | `text-popover-foreground` | Testo overlay dialog |

### Meccanismo di Switch Automatico

Le variabili CSS sottostanti (`--background`, `--foreground`, ecc.) cambiano valore nel selettore `.dark`, garantendo adattamento immediato al tema attivo senza logica JavaScript aggiuntiva.

**Esempio (configurazione Tailwind CSS variables):**

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;
  /* ... altre variabili */
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;
  /* ... altre variabili */
}
```

Il componente Dialog eredita automaticamente i valori corretti in base alla presenza/assenza della classe `.dark` sul root element.

[Fonti: `docs/prompt-for-lovable_V0.md` L50–L53; `docs/stories/3.5.in-app-user-guide.md` L22, L42]

---

## 5. Checklist Implementazione Dialog

### Pre-Implementazione
- [ ] Verifica installazione Shadcn/UI (vedi `docs/architecture/addendum-tailwind-shadcn-setup.md`)
- [ ] Installazione componente Dialog: `npx shadcn@latest add dialog`
- [ ] Alias path configurati in `vite.config.ts` e `tsconfig.json`

### Implementazione
- [ ] Componente Dialog con struttura base (Trigger, Content, Header, Title, Description)
- [ ] `DialogTrigger` con `aria-label` descrittivo
- [ ] `DialogContent` con classi responsive (`sm:max-w-[...]`, `max-h-[...]`)
- [ ] Contenuto scrollabile se necessario (`overflow-y-auto`)
- [ ] Utilizzo esclusivo di variabili semantiche (no valori hard-coded)
- [ ] Pulsante chiusura con `DialogClose` e icona accessibile (`sr-only` label)

### Accessibilità
- [ ] `aria-label` su trigger (se solo icona)
- [ ] `DialogTitle` presente (obbligatorio per `aria-labelledby`)
- [ ] `DialogDescription` per contesto aggiuntivo
- [ ] Focus trap verificato (navigazione con `Tab` confinata)
- [ ] Chiusura con `Esc` funzionante
- [ ] Chiusura con click outside funzionante
- [ ] Focus ritorna a trigger dopo chiusura

### Theming
- [ ] Test rendering in tema Light
- [ ] Test rendering in tema Dark
- [ ] Verifica assenza colori hard-coded (ispezione CSS)
- [ ] Contrasto WCAG AA rispettato (4.5:1 testo normale, 3:1 testo grande)

### Testing
- [ ] Test E2E apertura/chiusura (Playwright)
- [ ] Test navigazione tastiera completa
- [ ] Test screen reader (NVDA/VoiceOver)
- [ ] Test switching tema durante sessione

[Fonte: `docs/qa/assessments/3.5-test-design-20250930.md`]

---

## 6. Troubleshooting Comune

### Problema: Dialog non si apre
- **Causa**: Mancanza di `DialogTrigger` o componente non wrappato correttamente
- **Soluzione**: Verifica che `DialogTrigger` abbia `asChild` e wrappato attorno a elemento interattivo

### Problema: Focus non ritorna a trigger dopo chiusura
- **Causa**: Trigger non è un elemento focusabile o `asChild` mancante
- **Soluzione**: Usa `DialogTrigger asChild` con `<Button>` o elemento con `tabindex="0"`

### Problema: Colori non cambiano con switch tema
- **Causa**: Uso di valori hex/rgb hard-coded invece di variabili semantiche
- **Soluzione**: Sostituire tutti i colori con classi Tailwind semantiche (`bg-background`, `text-foreground`, ecc.)

### Problema: Dialog non scrollabile con contenuti lunghi
- **Causa**: Mancanza di `max-h-[...]` e `overflow-y-auto` su `DialogContent`
- **Soluzione**: Aggiungere `max-h-[80vh] overflow-y-auto` a `DialogContent`

### Problema: Screen reader non annuncia il dialog
- **Causa**: Mancanza di `DialogTitle` o ID non collegati
- **Soluzione**: Assicurare presenza di `DialogTitle` (obbligatorio per `aria-labelledby`)

---

## 7. Riferimenti

- Shadcn/UI Dialog: https://ui.shadcn.com/docs/components/dialog
- Radix UI Dialog Primitive: https://www.radix-ui.com/primitives/docs/components/dialog
- WAI-ARIA Dialog Pattern: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- WCAG 2.1 AA Guidelines: https://www.w3.org/WAI/WCAG21/quickref/

## 8. Applicazioni nel Progetto

Componenti che usano o useranno Dialog:
- `HelpModal` (Story 3.5): guida in-app per studenti
- Conferme azioni critiche (future)
- Visualizzazione dettagli fonti (potenziale evoluzione Story 3.4)

[Fonte: `docs/stories/3.5.in-app-user-guide.md`]
