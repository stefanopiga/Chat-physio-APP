import React, { useEffect, useState } from "react";
import { authService } from "../services/authService";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
// Ottimizzazione: import specifici da recharts per tree-shaking
import { BarChart } from "recharts/lib/chart/BarChart";
import { Bar } from "recharts/lib/cartesian/Bar";
import { XAxis } from "recharts/lib/cartesian/XAxis";
import { YAxis } from "recharts/lib/cartesian/YAxis";
import { CartesianGrid } from "recharts/lib/cartesian/CartesianGrid";
import { Tooltip } from "recharts/lib/component/Tooltip";
import { ResponsiveContainer } from "recharts/lib/component/ResponsiveContainer";
import { Legend } from "recharts/lib/component/Legend";

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

// -------------------------------
// Types - Story 4.2.2 (Advanced)
// -------------------------------

interface TemporalDistribution {
  hour_slot: number;
  query_count: number;
  label: string;
}

interface QualityMetrics {
  avg_response_length_chars: number;
  avg_chunks_per_response: number;
  chunks_distribution: {
    min: number;
    max: number;
    median: number;
  };
}

interface ProblematicQuery {
  query_text: string;
  negative_feedback_count: number;
  first_seen: string;
}

interface ProblematicQueriesResponse {
  queries: ProblematicQuery[];
  total_count: number; // AC3: Total problematic queries count
}

interface EngagementStats {
  avg_session_duration_minutes: number;
  avg_queries_per_session: number;
  feedback_conversion_rate: number;
}

interface ChunkRetrievalStat {
  chunk_id: string;
  document_id: string;
  retrieval_count: number;
  avg_similarity_score: number;
}

interface ChunkRetrievalResponse {
  top_chunks: ChunkRetrievalStat[];
  total_chunks_count: number; // AC5: Total unique chunks used
}

interface AdvancedAnalyticsData extends AnalyticsData {
  temporal_distribution: TemporalDistribution[];
  quality_metrics: QualityMetrics;
  problematic_queries: ProblematicQueriesResponse; // AC3: includes total_count
  engagement_stats: EngagementStats;
  top_chunks: ChunkRetrievalResponse; // AC5: includes total_chunks_count
}

type FeedbackChartData = {
  name: string;
  count: number;
};

// -------------------------------
// Component
// -------------------------------

const AnalyticsPage: React.FC = () => {
  const [analytics, setAnalytics] = useState<AdvancedAnalyticsData | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeFilter, setTimeFilter] = useState<string>("week"); // AC7: Default "week"

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await authService.getSession();
      if (!data.session?.access_token) {
        throw new Error("Token di autenticazione mancante");
      }

      // AC7: Mappatura UI → API query param + AC9: include_advanced=true
      const res = await fetch(
        `/api/v1/admin/analytics?time_filter=${timeFilter}&include_advanced=true`,
        {
          headers: {
            Authorization: `Bearer ${data.session.access_token}`,
          },
        }
      );

      if (!res.ok) {
        throw new Error(`Errore HTTP ${res.status}: ${res.statusText}`);
      }

      const analyticsData = await res.json();

      // 🐛 DEBUG Story 4.2.3: Log analytics data
      console.log("[Analytics] Data received:", analyticsData);
      console.log(
        "[Analytics] Feedback Summary:",
        analyticsData?.feedback_summary
      );
      console.log(
        "[Analytics] Problematic Queries:",
        analyticsData?.problematic_queries
      );
      console.log("[Analytics] Engagement:", analyticsData?.engagement_stats);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeFilter]); // AC7: Refetch quando cambia time_filter

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
        <div className="flex items-center gap-4">
          {/* AC7: Time Filter Dropdown */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Periodo:</label>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="day">Ultimo Giorno</option>
              <option value="week">Ultima Settimana</option>
              <option value="month">Ultimo Mese</option>
              <option value="all">Tutto</option>
            </select>
            <span className="text-xs text-muted-foreground">UTC</span>
          </div>
          <button
            onClick={fetchAnalytics}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
            aria-label="Aggiorna dati analytics"
          >
            Aggiorna Dati
          </button>
        </div>
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

        {/* AC4: Engagement Stats Cards */}
        <h3 className="text-md mt-6 font-semibold">Engagement</h3>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardDescription>Tempo Medio Sessione</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.engagement_stats.avg_session_duration_minutes.toFixed(
                  1
                )}{" "}
                min
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Query per Sessione</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.engagement_stats.avg_queries_per_session.toFixed(1)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Tasso Conversione Feedback</CardDescription>
              <CardTitle className="text-3xl">
                {(
                  analytics.engagement_stats.feedback_conversion_rate * 100
                ).toFixed(1)}
                %
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

      {/* AC1: Temporal Distribution Section */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Distribuzione Temporale</h2>
        <Card>
          <CardContent className="pt-6">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.temporal_distribution}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    tick={{ fill: "#6b7280", fontSize: 12 }}
                  />
                  <YAxis
                    label={{
                      value: "Query Count",
                      angle: -90,
                      position: "insideLeft",
                    }}
                  />
                  <Tooltip />
                  <Bar
                    dataKey="query_count"
                    fill="#3b82f6"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              Picco:{" "}
              {analytics.temporal_distribution.reduce(
                (max, item) =>
                  item.query_count > max.query_count ? item : max,
                analytics.temporal_distribution[0]
              )?.label || "N/A"}
            </p>
          </CardContent>
        </Card>
      </section>

      {/* AC2: Quality Metrics Section */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Qualità Risposte</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardDescription>Lunghezza Media</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.quality_metrics.avg_response_length_chars} char
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Chunk per Risposta</CardDescription>
              <CardTitle className="text-3xl">
                {analytics.quality_metrics.avg_chunks_per_response.toFixed(1)}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <CardDescription>Chunk Range</CardDescription>
              <CardTitle className="text-xl">
                {analytics.quality_metrics.chunks_distribution.min} -{" "}
                {analytics.quality_metrics.chunks_distribution.max}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Mediana: {analytics.quality_metrics.chunks_distribution.median}
              </p>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* AC3: Problematic Queries Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Query Problematiche</h2>
          <p className="text-sm text-muted-foreground">
            Totale: {analytics.problematic_queries.total_count}
          </p>
        </div>
        <Card>
          <CardContent className="p-0">
            {analytics.problematic_queries.queries.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Nessuna query problematica identificata
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left text-sm">
                      <th scope="col" className="p-4 font-medium">
                        Query
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Feedback Negativi
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Prima Segnalazione
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.problematic_queries.queries.map((q, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="p-4 text-sm">{q.query_text}</td>
                        <td className="p-4 text-right text-sm font-medium text-destructive">
                          {q.negative_feedback_count}
                        </td>
                        <td className="p-4 text-right text-sm text-muted-foreground">
                          {new Date(q.first_seen).toLocaleDateString("it-IT")}
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

      {/* AC5: Top Chunks Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Chunk Più Utilizzati</h2>
          <p className="text-sm text-muted-foreground">
            Chunk Unici: {analytics.top_chunks.total_chunks_count}
          </p>
        </div>
        <Card>
          <CardContent className="p-0">
            {analytics.top_chunks.top_chunks.length === 0 ? (
              <p className="p-6 text-center text-sm text-muted-foreground">
                Dati chunk non disponibili
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b">
                    <tr className="text-left text-sm">
                      <th scope="col" className="p-4 font-medium">
                        Documento
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Utilizzi
                      </th>
                      <th scope="col" className="p-4 font-medium text-right">
                        Similarità Media
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.top_chunks.top_chunks.map((chunk, idx) => (
                      <tr key={idx} className="border-b last:border-0">
                        <td className="p-4 text-xs font-mono">
                          {chunk.document_id}
                        </td>
                        <td className="p-4 text-right text-sm font-medium">
                          {chunk.retrieval_count}
                        </td>
                        <td className="p-4 text-right text-sm">
                          {chunk.avg_similarity_score.toFixed(3)}
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
    </div>
  );
};

export default AnalyticsPage;
