import React, { memo } from "react";
import ChunkCard from "./ChunkCard";

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

const ChunkList: React.FC<ChunkListProps> = memo(({ chunks }) => {
  const isEmpty = !chunks || chunks.length === 0;

  return (
    <section className="space-y-2">
      <h2 className="text-xl font-semibold">
        Chunk Recuperati ({chunks?.length ?? 0})
      </h2>
      {isEmpty && (
        <div className="text-sm text-muted-foreground">
          Nessun chunk recuperato. Verifica la base di conoscenza.
        </div>
      )}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {chunks?.map((chunk, idx) => (
          <ChunkCard
            key={`${chunk.chunk_id ?? "unknown"}-${idx}`}
            chunk={chunk}
          />
        ))}
      </div>
    </section>
  );
});

ChunkList.displayName = "ChunkList";

export default ChunkList;

