import React from "react";

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

const ChunkCard: React.FC<ChunkCardProps> = ({ chunk }) => {
  const title =
    chunk.metadata?.document_name ||
    chunk.metadata?.document_id ||
    chunk.chunk_id ||
    "Chunk";

  const scoreDisplay =
    typeof chunk.similarity_score === "number"
      ? chunk.similarity_score.toFixed(3)
      : "N/A";

  const contentPreview = chunk.content
    ? chunk.content.slice(0, 200)
    : "";
  const hasMore = chunk.content && chunk.content.length > 200;

  return (
    <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-medium">{title}</div>
        <span className="inline-flex items-center rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
          Score: {scoreDisplay}
        </span>
      </div>
      <div className="text-sm text-muted-foreground">
        {contentPreview}
        {hasMore ? "…" : ""}
      </div>
      <details className="mt-2">
        <summary className="cursor-pointer text-sm">Metadati</summary>
        <div className="mt-2 text-xs text-muted-foreground">
          <div>document_id: {chunk.metadata?.document_id ?? ""}</div>
          <div>page_number: {chunk.metadata?.page_number ?? ""}</div>
          <div>
            chunking_strategy: {chunk.metadata?.chunking_strategy ?? ""}
          </div>
        </div>
      </details>
    </div>
  );
};

export default ChunkCard;

