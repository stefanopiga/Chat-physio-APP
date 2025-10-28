import React, { useEffect, useState } from "react";
import { authService } from "../services/authService";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// -------------------------------
// Types
// -------------------------------

interface OverviewStats {
  total_queries: number;
  total_sessions: number;
  feedback_ratio: number;
  avg_latency_ms: number;
}

interface QueryStat {
  query_text: string;
  count: number;
  last_queried_at: string;
}

interface FeedbackSummary {
  thumbs_up: number;
  thumbs_down: number;
  ratio: number;
}

interface PerformanceMetrics {
  latency_p95_ms: number;
  latency_p99_ms: number;
  sample_count: number;
}

interface AnalyticsData {
  overview: OverviewStats;
  top_queries: QueryStat[];
  feedback_summary: FeedbackSummary;
  performance_metrics: PerformanceMetrics;
}

type FeedbackChartData = {
  name: string;
  count: number;
};

// -------------------------------
// Component
// -------------------------------

const AnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await authService.getSession();
      if (!data.session?.access_token) {
        throw new Error("Token di autenticazione mancante");
      }

      const res = await fetch("/api/v1/admin/analytics", {
        headers: {
          Authorization: `Bearer ${data.session.access_token}`,
        },
      });

      if (!res.ok) {
        throw new Error(`Errore HTTP ${res.status}: ${res.statusText}`);
      }

      const analyticsData = await res.json();
      setAnalytics(analyticsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore sconosciuto");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    authService.getSession().then(({ data: { session } }) => {
      if (session) {
        fetchAnalytics();
      } else {
        setLoading(false);
      }
    });
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-8 p-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Analytics Dashboard</h1>
          <p className="text-sm text-muted-foreground">Caricamento dati...</p>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 w-24 rounded bg-muted"></div>
                <div className="h-8 w-16 rounded bg-muted"></div>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="mx-auto max-w-6xl space-y-8 p-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Analytics Dashboard</h1>
          <p className="text-sm text-destructive">Errore: {error}</p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90"
        >
          Riprova
        </button>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="mx-auto max-w-6xl space-y-8 p-4">
        <p>Nessun dato disponibile</p>
      </div>
    );
  }

  // Transform feedback data per chart
  const feedbackData: FeedbackChartData[] = [
    { name: "Thumbs Up", count: analytics.feedback_summary.thumbs_up },
    { name: "Thumbs Down", count: analytics.feedback_summary.thumbs_down },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold">Analytics Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Statistiche aggregate sistema RAG
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
          aria-label="Aggiorna dati analytics"
        >
          Aggiorna Dati
        </button>
      </div>

      {/* Overview KPIs */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Panoramica</h2>
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader>
              <CardDescription>Domande Totali</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.overview.total_queries}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Sessioni Attive</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.overview.total_sessions}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Feedback Positivo</CardDescription>
              <CardTitle className="text-3xl">
                {(analytics.overview.feedback_ratio * 100).toFixed(1)}%
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Latenza Media</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.overview.avg_latency_ms}ms
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Top Queries Table */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Domande Più Frequenti</h2>
        <Card>
          <CardContent className="p-0">
            {analytics.top_queries.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Nessuna domanda registrata
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left text-sm">
                      <th scope="col" className="p-4 font-medium">
                        Domanda
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Occorrenze
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Ultima Query
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.top_queries.map((q, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="p-4 text-sm">{q.query_text}</td>
                        <td className="p-4 text-right text-sm font-medium">
                          {q.count}
                        </td>
                        <td className="p-4 text-right text-sm text-muted-foreground">
                          {q.last_queried_at
                            ? new Date(q.last_queried_at).toLocaleString(
                                "it-IT"
                              )
                            : "N/A"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Feedback Chart */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Feedback Aggregato</h2>
        <Card>
          <CardContent className="pt-6">
            {analytics.feedback_summary.thumbs_up +
              analytics.feedback_summary.thumbs_down ===
            0 ? (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Nessun feedback ricevuto
              </p>
            ) : (
              <>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={feedbackData}
                      margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#6b7280" }}
                        axisLine={{ stroke: "#d1d5db" }}
                      />
                      <YAxis
                        tick={{ fill: "#6b7280" }}
                        axisLine={{ stroke: "#d1d5db" }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#ffffff",
                          border: "1px solid #e5e7eb",
                          borderRadius: "8px",
                        }}
                        cursor={{ fill: "rgba(59, 130, 246, 0.1)" }}
                      />
                      <Legend />
                      <Bar
                        dataKey="count"
                        fill="#22c55e"
                        radius={[8, 8, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-4 text-center text-sm text-muted-foreground">
                  Ratio positivo:{" "}
                  {(analytics.feedback_summary.ratio * 100).toFixed(1)}%
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Performance Metrics */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Performance Sistema</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>P95 Latency</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold">
                  {analytics.performance_metrics.latency_p95_ms}ms
                </span>
                {analytics.performance_metrics.latency_p95_ms > 2000 && (
                  <span className="inline-flex items-center rounded-full border border-destructive bg-destructive/10 px-2 py-1 text-xs text-destructive">
                    ⚠ High
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>P99 Latency</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold">
                  {analytics.performance_metrics.latency_p99_ms}ms
                </span>
                {analytics.performance_metrics.latency_p99_ms > 2000 && (
                  <span className="inline-flex items-center rounded-full border border-destructive bg-destructive/10 px-2 py-1 text-xs text-destructive">
                    ⚠ High
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
        <p className="text-sm text-muted-foreground">
          Campioni: {analytics.performance_metrics.sample_count}
        </p>
      </section>
    </div>
  );
};

export default AnalyticsPage;
