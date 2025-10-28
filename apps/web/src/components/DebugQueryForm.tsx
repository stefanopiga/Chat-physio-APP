import React, { useState } from "react";

interface DebugQueryFormProps {
  onSubmit: (question: string) => Promise<void>;
  isLoading: boolean;
}

const DebugQueryForm: React.FC<DebugQueryFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const [question, setQuestion] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    await onSubmit(q);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <label htmlFor="question" className="block text-sm font-medium">
        Domanda di test
      </label>
      <textarea
        id="question"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Inserisci una domanda per testare il retrieval e la generazione..."
        className="min-h-24 w-full resize-y rounded-md border border-input bg-background p-3 text-foreground shadow-sm outline-none ring-offset-background placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:ring-offset-2"
        aria-label="Domanda di test per debug RAG"
      />
      <button
        type="submit"
        className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 focus:outline-hidden focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50"
        disabled={isLoading || !question.trim()}
      >
        {isLoading ? "Elaborazione query in corso..." : "Esegui Query Debug"}
      </button>
    </form>
  );
};

export default DebugQueryForm;

