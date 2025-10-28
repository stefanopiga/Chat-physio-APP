import { useState, useEffect } from "react";
import { Plus, Copy, Trash2, Check, AlertCircle } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { supabase } from "../lib/supabaseClient";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";

interface StudentToken {
  id: string;
  first_name: string;
  last_name: string;
  token: string;
  is_active: boolean;
  expires_at: string;
  created_at: string;
  updated_at: string;
}

interface GeneratedToken {
  id: string;
  token: string;
  first_name: string;
  last_name: string;
  expires_at: string;
}

export default function StudentTokensPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [tokens, setTokens] = useState<StudentToken[]>([]);
  const [generatedToken, setGeneratedToken] = useState<GeneratedToken | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [tokenToRevoke, setTokenToRevoke] = useState<StudentToken | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

  const getAuthToken = async (): Promise<string | null> => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    return session?.access_token || null;
  };

  useEffect(() => {
    fetchTokens();
  }, [showInactive]);

  const fetchTokens = async () => {
    try {
      setIsLoadingList(true);
      const token = await getAuthToken();
      if (!token) {
        setError("Token autenticazione mancante");
        return;
      }

      const url = `${API_BASE_URL}/api/v1/admin/student-tokens?is_active=${!showInactive ? "true" : ""}`;
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Errore ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setTokens(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore nel caricamento dei token"
      );
    } finally {
      setIsLoadingList(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!firstName.trim() || !lastName.trim()) {
      setError("Nome e cognome sono obbligatori");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const token = await getAuthToken();
      if (!token) {
        setError("Token autenticazione mancante");
        return;
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/student-tokens`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            first_name: firstName,
            last_name: lastName,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Errore ${response.status}`);
      }

      const data = await response.json();
      setGeneratedToken(data);
      setFirstName("");
      setLastName("");
      fetchTokens();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore nella creazione del token"
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyToken = async () => {
    if (!generatedToken) return;

    try {
      await navigator.clipboard.writeText(generatedToken.token);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      setError("Impossibile copiare il token");
    }
  };

  const handleRevokeClick = (token: StudentToken) => {
    setTokenToRevoke(token);
    setRevokeDialogOpen(true);
  };

  const handleRevokeConfirm = async () => {
    if (!tokenToRevoke) return;

    try {
      const token = await getAuthToken();
      if (!token) {
        setError("Token autenticazione mancante");
        return;
      }

      const response = await fetch(
        `${API_BASE_URL}/api/v1/admin/student-tokens/${tokenToRevoke.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Errore ${response.status}: ${response.statusText}`);
      }

      fetchTokens();
      setRevokeDialogOpen(false);
      setTokenToRevoke(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Errore nella revoca del token"
      );
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("it-IT", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const isExpired = (dateString: string) => {
    return new Date(dateString) < new Date();
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Gestione Token Studenti</h1>
        <p className="text-muted-foreground">
          Crea e gestisci token di accesso annuali per studenti registrati
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Form Creazione Token */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Crea Nuovo Token</CardTitle>
          <CardDescription>
            Genera un token di accesso valido per 1 anno
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">Nome</Label>
                <Input
                  id="firstName"
                  placeholder="Nome studente"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Cognome</Label>
                <Input
                  id="lastName"
                  placeholder="Cognome studente"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                />
              </div>
            </div>
            <Button
              type="submit"
              disabled={isLoading || !firstName.trim() || !lastName.trim()}
            >
              <Plus className="mr-2 h-4 w-4" />
              {isLoading ? "Generazione..." : "Genera Token"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Token Generato */}
      {generatedToken && (
        <Alert className="mb-8 border-green-500 bg-green-50">
          <Check className="h-4 w-4 text-green-600" />
          <AlertDescription>
            <div className="space-y-3">
              <p className="font-medium text-green-900">
                Token generato con successo per {generatedToken.first_name}{" "}
                {generatedToken.last_name}
              </p>
              <div className="bg-white p-3 rounded border border-green-200">
                <code
                  className="font-mono text-sm break-all"
                  data-testid="generated-token"
                >
                  {generatedToken.token}
                </code>
              </div>
              <div className="flex items-center gap-4">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCopyToken}
                  className="gap-2"
                >
                  {copied ? (
                    <>
                      <Check className="h-4 w-4" />
                      Copiato!
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" />
                      Copia Token
                    </>
                  )}
                </Button>
                <p className="text-sm text-muted-foreground">
                  Scadenza: {formatDate(generatedToken.expires_at)}
                </p>
              </div>
              <p className="text-sm text-muted-foreground">
                Invia questo token allo studente via mail. Lo studente potrà
                usarlo nella schermata di login.
              </p>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Lista Token */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Token Studenti</CardTitle>
              <CardDescription>Elenco dei token creati</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowInactive(!showInactive)}
            >
              {showInactive ? "Mostra solo attivi" : "Mostra anche revocati"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingList ? (
            <div className="text-center py-8 text-muted-foreground">
              Caricamento...
            </div>
          ) : tokens.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Nessun token creato. Usa il form sopra per generare il primo.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Cognome</TableHead>
                  <TableHead>Token</TableHead>
                  <TableHead>Scadenza</TableHead>
                  <TableHead>Stato</TableHead>
                  <TableHead>Azioni</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tokens.map((token) => (
                  <TableRow key={token.id}>
                    <TableCell>{token.first_name}</TableCell>
                    <TableCell>{token.last_name}</TableCell>
                    <TableCell>
                      <code className="text-sm" title={token.token}>
                        {token.token.substring(0, 8)}...
                      </code>
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          isExpired(token.expires_at) ? "text-red-600" : ""
                        }
                      >
                        {formatDate(token.expires_at)}
                        {isExpired(token.expires_at) && (
                          <Badge variant="destructive" className="ml-2">
                            Scaduto
                          </Badge>
                        )}
                      </span>
                    </TableCell>
                    <TableCell>
                      {token.is_active ? (
                        <Badge variant="default">Attivo</Badge>
                      ) : (
                        <Badge variant="secondary">Revocato</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {token.is_active && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleRevokeClick(token)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Revoca
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Dialog Revoca */}
      <Dialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Conferma Revoca</DialogTitle>
            <DialogDescription>
              Sei sicuro di voler revocare l'accesso per{" "}
              <strong>
                {tokenToRevoke?.first_name} {tokenToRevoke?.last_name}
              </strong>
              ? Lo studente non potrà più utilizzare questo token.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRevokeDialogOpen(false)}
            >
              Annulla
            </Button>
            <Button variant="destructive" onClick={handleRevokeConfirm}>
              Revoca
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
