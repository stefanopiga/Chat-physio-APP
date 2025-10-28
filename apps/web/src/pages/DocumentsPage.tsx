import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/authService";

interface DocumentSummary {
  document_id: string;
  document_name: string;
  upload_date: string;
  chunk_count: number;
  primary_chunking_strategy: string | null;
}

interface DocumentListResponse {
  documents: DocumentSummary[];
  total_count: number;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: sessionData } = await authService.getSession();
      if (!sessionData.session?.access_token) {
        throw new Error("Token di autenticazione mancante");
      }

      const response = await fetch("/api/v1/admin/documents", {
        headers: {
          Authorization: `Bearer ${sessionData.session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: DocumentListResponse = await response.json();
      setDocuments(data.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore sconosciuto");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (isoString: string) => {
    if (!isoString) return "N/A";
    const date = new Date(isoString);
    return date.toLocaleDateString("it-IT");
  };

  const getStrategyColor = (strategy: string | null) => {
    if (!strategy) return "secondary";
    switch (strategy) {
      case "recursive":
        return "default";
      case "semantic":
        return "default";
      case "by_title":
        return "default";
      case "by_page":
        return "default";
      default:
        return "secondary";
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl space-y-6 p-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">Document Explorer</h1>
          <p className="text-muted-foreground">
            Visualizza e analizza chunk generati per ogni documento
          </p>
        </div>
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
        <div className="space-y-1">
          <h1 className="text-3xl font-bold">Document Explorer</h1>
          <p className="text-muted-foreground">
            Visualizza e analizza chunk generati per ogni documento
          </p>
        </div>
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
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">Document Explorer</h1>
        <p className="text-muted-foreground">
          Visualizza e analizza chunk generati per ogni documento
        </p>
      </div>

      {documents.length === 0 ? (
        <Card className="p-8">
          <div className="text-muted-foreground flex items-center justify-center">
            Nessun documento trovato
          </div>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left">
                  <th scope="col" className="p-4 font-semibold">
                    Documento
                  </th>
                  <th scope="col" className="p-4 font-semibold">
                    Data Upload
                  </th>
                  <th scope="col" className="p-4 font-semibold">
                    Chunk Count
                  </th>
                  <th scope="col" className="p-4 font-semibold">
                    Strategia
                  </th>
                  <th scope="col" className="p-4 font-semibold">
                    Azioni
                  </th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr
                    key={doc.document_id}
                    className="border-b last:border-b-0"
                  >
                    <td className="p-4 font-medium">{doc.document_name}</td>
                    <td className="p-4 text-muted-foreground">
                      {formatDate(doc.upload_date)}
                    </td>
                    <td className="p-4">{doc.chunk_count}</td>
                    <td className="p-4">
                      <Badge
                        variant={getStrategyColor(
                          doc.primary_chunking_strategy
                        )}
                      >
                        {doc.primary_chunking_strategy || "N/A"}
                      </Badge>
                    </td>
                    <td className="p-4">
                      <Link to={`/admin/documents/${doc.document_id}/chunks`}>
                        <Button size="sm">Visualizza Chunk</Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
