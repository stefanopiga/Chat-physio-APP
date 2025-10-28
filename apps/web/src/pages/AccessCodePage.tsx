import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const AccessCodePage: React.FC = () => {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);

    if (code.trim() === "") {
      setError("Il campo codice non può essere vuoto.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/exchange-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_code: code.trim() }),
      });

      if (!res.ok) {
        const message = await res.text();
        throw new Error(
          message || `Errore di validazione codice (${res.status})`
        );
      }

      const data: { token: string; token_type: string; expires_in: number } =
        await res.json();

      // Persisti token temporaneo in sessionStorage; usato per accesso anonimo/limitato
      sessionStorage.setItem("temp_jwt", data.token);

      // Redirect alla chat dopo successo
      navigate("/chat");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Si è verificato un errore sconosciuto.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4 bg-background">
      <div className="mx-auto w-full max-w-md space-y-4">
        <h1 className="text-2xl font-semibold text-center">Accesso Studente</h1>
        <form onSubmit={onSubmit} className="space-y-3">
        <div className="space-y-1.5">
          <label htmlFor="access_code" className="text-sm font-medium">
            Codice di accesso
          </label>
          <input
            id="access_code"
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Inserisci il codice"
            className="w-full rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          {error && (
            <p role="alert" className="mt-1 text-sm text-destructive">
              {error}
            </p>
          )}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="inline-flex w-full items-center justify-center rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Verifica..." : "Entra"}
        </button>
      </form>
      </div>
    </div>
  );
};

export default AccessCodePage;
