import React from "react";
import { HelpCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const HelpModal: React.FC = () => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          className="rounded-sm p-2 text-foreground opacity-70 transition-opacity hover:bg-accent hover:opacity-100 focus:ring-2 focus:ring-ring focus:ring-offset-2 focus:outline-hidden"
          aria-label="Apri guida"
        >
          <HelpCircle className="h-5 w-5" />
        </button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Guida all'uso di FisioRAG</DialogTitle>
          <DialogDescription>
            Scopri come utilizzare la chat per ottenere il massimo dalle tue domande.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 py-4">
          {/* Benvenuto */}
          <section className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">Benvenuto!</h3>
            <p className="text-sm text-muted-foreground">
              FisioRAG è il tuo assistente didattico per la fisioterapia. Fornisce risposte basate esclusivamente sui materiali del corso.
            </p>
          </section>

          {/* Come Porre Domande */}
          <section className="rounded-lg border border-border bg-card p-4 text-card-foreground">
            <h3 className="mb-2 text-lg font-semibold">Come Porre Domande</h3>
            <p className="text-sm text-muted-foreground">
              Sii specifico: indica argomento, distretto anatomico e obiettivo (es. valutazione, trattamento). Usa i termini tecnici del corso e parole chiave rilevanti per ridurre l'ambiguità.
            </p>
          </section>

          {/* Come Funzionano le Fonti */}
          <section className="rounded-lg border border-border bg-card p-4 text-card-foreground">
            <h3 className="mb-2 text-lg font-semibold">Come Funzionano le Fonti</h3>
            <p className="text-sm text-muted-foreground">
              Accanto alle risposte trovi citazioni numerate. Cliccando su una citazione si apre un riquadro con l'estratto originale del documento e i metadati essenziali.
            </p>
          </section>

          {/* Aiutaci a Migliorare */}
          <section className="rounded-lg border border-border bg-card p-4 text-card-foreground">
            <h3 className="mb-2 text-lg font-semibold">Aiutaci a Migliorare</h3>
            <p className="text-sm text-muted-foreground">
              I pulsanti 👍/👎 servono a valutare la qualità della risposta e a migliorare pertinenza e accuratezza future. Usa 👍 quando la risposta è utile e corretta; usa 👎 quando è incompleta o poco pertinente.
            </p>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default HelpModal;
