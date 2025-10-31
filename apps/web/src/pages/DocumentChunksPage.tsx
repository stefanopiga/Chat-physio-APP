import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { authService } from "@/services/authService";

interface ChunkDetail {
  chunk_id: string;
  content: string;
  chunk_size: number;
  chunk_index: number | null;
  chunking_strategy: string | null;
  page_number: number | null;
  embedding_status: "indexed" | "pending";
  created_at: string;
}

interface DocumentChunksResponse {
  document_id: string;
  document_name: string | null;
  chunks: ChunkDetail[];
  total_chunks: number;
}

export default function DocumentChunksPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [chunks, setChunks] = useState<ChunkDetail[]>([]);
  const [documentName, setDocumentName] = useState<string>("");
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [strategyFilter, setStrategyFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("chunk_index");

  const fetchChunks = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: sessionData } = await authService.getSession();
      if (!sessionData.session?.access_token) {
        throw new Error("Token di autenticazione mancante");
      }

      const params = new URLSearchParams();
      if (strategyFilter !== "all") {
        params.append("strategy", strategyFilter);
      }
      if (sortBy) {
        params.append("sort_by", sortBy);
      }

      const url = `/api/v1/admin/documents/${documentId}/chunks?${params.toString()}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${sessionData.session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: DocumentChunksResponse = await response.json();
      setChunks(data.chunks);
      setDocumentName(data.document_name || "Documento");
      setTotalChunks(data.total_chunks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore sconosciuto");
    } finally {
      setLoading(false);
    }
  }, [documentId, strategyFilter, sortBy]);

  useEffect(() => {
    if (documentId) {
      void fetchChunks();
    }
  }, [documentId, fetchChunks]);

  const handleStrategyFilter = (value: string) => {
    setStrategyFilter(value);
  };

  const handleSort = (value: string) => {
    setSortBy(value);
  };

  const getEmbeddingBadgeVariant = (status: "indexed" | "pending") => {
    return status === "indexed" ? "default" : "secondary";
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-4">
        <Card className="p-8">
          <div className="flex items-center justify-center">
            <div className="text-muted-foreground">Caricamento...</div>
          </div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-4">
        <Card className="border-destructive p-8">
          <div className="flex items-center justify-center text-destructive">
            Errore: {error}
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Link
            to="/admin/documents"
            className="text-muted-foreground hover:text-foreground text-sm"
          >
            ← Torna ai documenti
          </Link>
          <h1 className="text-3xl font-bold">{documentName}</h1>
          <p className="text-muted-foreground">{totalChunks} chunk generati</p>
        </div>

        <div className="flex gap-2">
          <Select value={strategyFilter} onValueChange={handleStrategyFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Strategia" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tutte</SelectItem>
              <SelectItem value="recursive">Recursive</SelectItem>
              <SelectItem value="semantic">Semantic</SelectItem>
              <SelectItem value="by_title">By Title</SelectItem>
              <SelectItem value="by_page">By Page</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={handleSort}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Ordina per" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="chunk_index">Sequenza</SelectItem>
              <SelectItem value="chunk_size">Dimensione</SelectItem>
              <SelectItem value="created_at">Data</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {chunks.length === 0 ? (
        <Card className="p-8">
          <div className="text-muted-foreground flex items-center justify-center">
            Nessun chunk trovato
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {chunks.map((chunk) => (
            <Card key={chunk.chunk_id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-sm">
                      Chunk #
                      {chunk.chunk_index !== null ? chunk.chunk_index : "N/A"}
                    </CardTitle>
                    <CardDescription>
                      {chunk.chunk_size} caratteri |{" "}
                      {chunk.chunking_strategy || "N/A"}
                      {chunk.page_number && ` | Pagina ${chunk.page_number}`}
                    </CardDescription>
                  </div>
                  <Badge
                    variant={getEmbeddingBadgeVariant(chunk.embedding_status)}
                  >
                    {chunk.embedding_status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-sm">
                  {chunk.content.length > 300
                    ? chunk.content.substring(0, 300) + "..."
                    : chunk.content}
                </div>
                {chunk.content.length > 300 && (
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="link" size="sm" className="mt-2 p-0">
                        Mostra contenuto completo
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-h-[600px] overflow-y-auto sm:max-w-[600px]">
                      <DialogHeader>
                        <DialogTitle>
                          Chunk #
                          {chunk.chunk_index !== null
                            ? chunk.chunk_index
                            : "N/A"}{" "}
                          - Contenuto Completo
                        </DialogTitle>
                      </DialogHeader>
                      <div className="whitespace-pre-wrap text-sm">
                        {chunk.content}
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
