/**
 * Unit tests - AnalyticsPage (Story 4.2)
 * 
 * Test cases:
 * 1. Rendering: heading "Analytics Dashboard" presente
 * 2. Loading state: skeleton cards visibili durante fetch
 * 3. KPI cards: 4 card overview renderate con dati mock
 * 4. Query table: righe query con sort by count
 * 5. Feedback chart: visualizzazione up/down con ratio
 * 6. Performance metrics: p95/p99 displayati correttamente
 * 7. Refresh button: click trigger re-fetch analytics
 * 8. Error state: messaggio errore se fetch fallisce
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import AnalyticsPage from '../AnalyticsPage';
import { authService } from '@/services/authService';

// Mock authService
vi.mock('@/services/authService', () => ({
  authService: {
    getSession: vi.fn(),
  },
}));

// Mock fetch
global.fetch = vi.fn();

const mockSession = {
  access_token: 'mock-admin-token',
  user: { email: 'admin@test.com' },
};

const mockAnalyticsData = {
  overview: {
    total_queries: 150,
    total_sessions: 25,
    feedback_ratio: 0.75,
    avg_latency_ms: 450,
  },
  top_queries: [
    { query_text: 'cos\'è la scoliosi?', count: 10, last_queried_at: '2025-10-02T10:00:00Z' },
    { query_text: 'esercizi lombari', count: 8, last_queried_at: '2025-10-02T11:00:00Z' },
    { query_text: 'terapia manuale cervicale', count: 5, last_queried_at: '2025-10-02T12:00:00Z' },
  ],
  feedback_summary: {
    thumbs_up: 45,
    thumbs_down: 15,
    ratio: 0.75,
  },
  performance_metrics: {
    latency_p95_ms: 800,
    latency_p99_ms: 1200,
    sample_count: 150,
  },
};

const renderAnalyticsPage = () => {
  return render(
    <BrowserRouter>
      <AnalyticsPage />
    </BrowserRouter>
  );
};

describe('AnalyticsPage', () => {
  beforeEach(() => {
    cleanup();
    vi.clearAllMocks();
    (authService.getSession as any).mockResolvedValue({ data: { session: mockSession } });
    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockAnalyticsData,
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it('FT-001: renders heading "Analytics Dashboard"', async () => {
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });
  });

  it('FT-002: displays skeleton cards during loading', async () => {
    // Delay fetch per catturare loading state
    (global.fetch as any).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({
        ok: true,
        json: async () => mockAnalyticsData,
      }), 100))
    );

    renderAnalyticsPage();

    // Loading state visibile immediatamente
    expect(screen.getByText('Caricamento dati...')).toBeInTheDocument();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText('Caricamento dati...')).not.toBeInTheDocument();
    });
  });

  it('FT-003: renders 4 KPI cards with correct data', async () => {
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Domande Totali')).toBeInTheDocument();
      expect(screen.getByText('150')).toBeInTheDocument();

      expect(screen.getByText('Sessioni Attive')).toBeInTheDocument();
      expect(screen.getByText('25')).toBeInTheDocument();

      expect(screen.getByText('Feedback Positivo')).toBeInTheDocument();
      expect(screen.getByText('75.0%')).toBeInTheDocument();

      expect(screen.getByText('Latenza Media')).toBeInTheDocument();
      expect(screen.getByText('450ms')).toBeInTheDocument();
    });
  });

  it('FT-004: renders top queries table with sorted rows', async () => {
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Domande Più Frequenti')).toBeInTheDocument();

      // Verifica presenza query
      expect(screen.getByText('cos\'è la scoliosi?')).toBeInTheDocument();
      expect(screen.getByText('esercizi lombari')).toBeInTheDocument();
      expect(screen.getByText('terapia manuale cervicale')).toBeInTheDocument();

      // Verifica counts
      const rows = screen.getAllByRole('row');
      expect(rows.length).toBeGreaterThan(3); // Header + 3 data rows
    });
  });

  it('FT-005: renders feedback chart with up/down ratio', async () => {
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Feedback Aggregato')).toBeInTheDocument();

      // Verifica ratio display (usa query più specifica)
      const ratioText = screen.getByText(/Ratio positivo:/);
      expect(ratioText).toBeInTheDocument();
      expect(ratioText.textContent).toContain('75.0%');
    });
  });

  it('FT-006: displays performance metrics P95/P99', async () => {
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Performance Sistema')).toBeInTheDocument();

      expect(screen.getByText('P95 Latency')).toBeInTheDocument();
      expect(screen.getByText('800ms')).toBeInTheDocument();

      expect(screen.getByText('P99 Latency')).toBeInTheDocument();
      expect(screen.getByText('1200ms')).toBeInTheDocument();

      expect(screen.getByText(/Campioni: 150/)).toBeInTheDocument();
    });
  });

  it('FT-007: refresh button triggers re-fetch', async () => {
    const user = userEvent.setup();
    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Analytics Dashboard')).toBeInTheDocument();
    });

    // Initial fetch call
    expect(global.fetch).toHaveBeenCalledTimes(1);

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: /Aggiorna dati analytics/i });
    await user.click(refreshButton);

    // Verifica secondo fetch
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  it('FT-008: displays error message when fetch fails', async () => {
    (global.fetch as any).mockRejectedValue(new Error('Network error'));

    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText(/Errore: Network error/)).toBeInTheDocument();
    });

    // Verifica button retry presente
    expect(screen.getByRole('button', { name: /Riprova/i })).toBeInTheDocument();
  });

  it('FT-009: displays threshold warning for high P95 latency', async () => {
    const highLatencyData = {
      ...mockAnalyticsData,
      performance_metrics: {
        latency_p95_ms: 2500, // > 2000ms threshold
        latency_p99_ms: 3000,
        sample_count: 100,
      },
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => highLatencyData,
    });

    renderAnalyticsPage();

    await waitFor(() => {
      // Verifica badge warning presente
      const warningBadges = screen.getAllByText(/⚠ High/);
      expect(warningBadges.length).toBeGreaterThan(0);
    });
  });

  it('FT-010: displays empty state when no queries', async () => {
    const emptyData = {
      overview: {
        total_queries: 0,
        total_sessions: 0,
        feedback_ratio: 0.0,
        avg_latency_ms: 0,
      },
      top_queries: [],
      feedback_summary: {
        thumbs_up: 0,
        thumbs_down: 0,
        ratio: 0.0,
      },
      performance_metrics: {
        latency_p95_ms: 0,
        latency_p99_ms: 0,
        sample_count: 0,
      },
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => emptyData,
    });

    renderAnalyticsPage();

    await waitFor(() => {
      expect(screen.getByText('Nessuna domanda registrata')).toBeInTheDocument();
      expect(screen.getByText('Nessun feedback ricevuto')).toBeInTheDocument();
    });
  });
});

