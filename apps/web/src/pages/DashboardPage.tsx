import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { authService } from "../services/authService";
import type { Session } from "@supabase/supabase-js";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

const DashboardPage: React.FC = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    authService.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl space-y-6 p-4 pt-20">
        <p>Caricamento dashboard...</p>
      </div>
    );
  }

  const userEmail = session?.user?.email || "Amministratore";

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 pt-20">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Dashboard Amministratore</h1>
        <p className="text-sm text-muted-foreground">Benvenuto, {userEmail}</p>
      </div>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Funzionalità Admin</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Link to="/admin/debug" aria-label="Vai a Debug RAG">
            <Card className="transition-colors hover:bg-accent">
              <CardHeader>
                <CardTitle>Debug RAG</CardTitle>
                <CardDescription>
                  Visualizza chunk recuperati e risposte LLM per query di test
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link to="/admin/analytics" aria-label="Vai a Analytics Dashboard">
            <Card className="transition-colors hover:bg-accent">
              <CardHeader>
                <CardTitle>Analytics Dashboard</CardTitle>
                <CardDescription>
                  Statistiche utilizzo, domande frequenti, distribuzione
                  argomenti
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link to="/admin/documents" aria-label="Vai a Document Explorer">
            <Card className="transition-colors hover:bg-accent">
              <CardHeader>
                <CardTitle>Document Explorer</CardTitle>
                <CardDescription>
                  Visualizza e analizza chunk generati per ogni documento
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>

          <Link
            to="/admin/student-tokens"
            aria-label="Vai a Gestione Token Studenti"
          >
            <Card className="transition-colors hover:bg-accent">
              <CardHeader>
                <CardTitle>Gestione Token Studenti</CardTitle>
                <CardDescription>
                  Crea e gestisci token di accesso annuali per studenti
                  registrati
                </CardDescription>
              </CardHeader>
            </Card>
          </Link>
        </div>
      </section>
    </div>
  );
};

export default DashboardPage;
