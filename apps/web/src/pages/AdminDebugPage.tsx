import React, { useCallback, useMemo, useState } from "react";
import apiClient from "../lib/apiClient";
import DebugQueryForm from "../components/DebugQueryForm";
import ChunkList from "../components/ChunkList";

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

type DebugResponse = {
  question: string;
  answer: string | null;
  chunks: DebugChunk[];
  retrieval_time_ms: number;
  generation_time_ms: number;
};

const AdminDebugPage: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<DebugResponse | null>(null);

  const handleSubmit = useCallback(async (question: string) => {
    setError(null);
    setData(null);
    setLoading(true);
    try {
      const res = await apiClient.adminDebugQuery(question);
      setData(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      if (message === "401") window.location.href = "/login";
      else if (message === "429")
        setError("Limite richieste raggiunto (rate limit)");
      else setError("Errore durante l'esecuzione della query di debug");
    } finally {
      setLoading(false);
    }
  }, []);

  const timing = useMemo(() => {
    if (!data) return null;
    return `Retrieval: ${data.retrieval_time_ms}ms | Generation: ${data.generation_time_ms}ms`;
  }, [data]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Debug RAG</h1>
        <p className="text-sm text-muted-foreground">
          Esegui query di test per visualizzare risposta finale e chunk
          intermedi recuperati dal sistema.
        </p>
      </div>

      <DebugQueryForm onSubmit={handleSubmit} isLoading={loading} />

      {error && (
        <p role="alert" className="text-destructive">
          {error}
        </p>
      )}

      {data && (
        <div className="space-y-6">
          <section className="space-y-2">
            <h2 className="text-xl font-semibold">Risposta Finale</h2>
            <div className="whitespace-pre-wrap rounded-md border border-border bg-card p-4 text-card-foreground">
              {data.answer || ""}
            </div>
            {timing && (
              <div className="text-xs text-muted-foreground">{timing}</div>
            )}
          </section>

          <ChunkList chunks={data.chunks} />
        </div>
      )}
    </div>
  );
};

export default AdminDebugPage;
