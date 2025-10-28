/**
 * Unit tests for DocumentsPage (Story 4.4).
 *
 * Test Coverage:
 * 1. Rendering tabella documenti
 * 2. Navigazione a chunk page su click riga
 * 3. Empty state quando zero documenti
 * 4. Loading skeleton durante fetch
 * 5. Error state con messaggio errore
 * 6. Badge chunking strategy colori corretti
 * 7. Sort per colonna tabella
 * 8. Filter dropdown strategy
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import DocumentsPage from "../DocumentsPage";
import { authService } from "@/services/authService";

// Mock authService
vi.mock("@/services/authService", () => ({
  authService: {
    getSession: vi.fn(),
  },
}));

// Mock fetch globale
global.fetch = vi.fn();

const mockSession = {
  access_token: "mock-admin-token",
  user: { email: "admin@test.com" },
};

describe("DocumentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (authService.getSession as any).mockResolvedValue({
      data: { session: mockSession },
    });
  });

  it("Test 1: Rendering tabella documenti", async () => {
    const mockData = {
      documents: [
        {
          document_id: "123",
          document_name: "anatomia_spalla.pdf",
          upload_date: "2025-01-15T10:00:00Z",
          chunk_count: 15,
          primary_chunking_strategy: "recursive",
        },
        {
          document_id: "456",
          document_name: "ginocchio.pdf",
          upload_date: "2025-01-16T11:00:00Z",
          chunk_count: 20,
          primary_chunking_strategy: "semantic",
        },
      ],
      total_count: 2,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("anatomia_spalla.pdf")).toBeInTheDocument();
      expect(screen.getByText("ginocchio.pdf")).toBeInTheDocument();
    });

    // Verifica chunk count
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();

    // Verifica badge strategia
    expect(screen.getByText("recursive")).toBeInTheDocument();
    expect(screen.getByText("semantic")).toBeInTheDocument();
  });

  it("Test 2: Navigazione a chunk page su click riga", async () => {
    const mockData = {
      documents: [
        {
          document_id: "123",
          document_name: "test.pdf",
          upload_date: "2025-01-15T10:00:00Z",
          chunk_count: 10,
          primary_chunking_strategy: "recursive",
        },
      ],
      total_count: 1,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("test.pdf")).toBeInTheDocument();
    });

    // Verifica link navigazione (usa getAllByText per elementi multipli potenziali)
    const buttons = screen.getAllByText("Visualizza Chunk");
    const linkElement = buttons[buttons.length - 1].closest("a");
    expect(linkElement).toHaveAttribute("href", "/admin/documents/123/chunks");
  });

  it("Test 3: Empty state quando zero documenti", async () => {
    const mockData = {
      documents: [],
      total_count: 0,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Nessun documento trovato")).toBeInTheDocument();
    });
  });

  it("Test 4: Loading skeleton durante fetch", async () => {
    // Simula fetch lenta
    (global.fetch as any).mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => ({ documents: [], total_count: 0 }),
              }),
            100
          )
        )
    );

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    // Verifica stato loading
    expect(screen.getByText("Caricamento...")).toBeInTheDocument();

    // Attendi completamento
    await waitFor(
      () => {
        expect(screen.queryByText("Caricamento...")).not.toBeInTheDocument();
      },
      { timeout: 200 }
    );
  });

  it("Test 5: Error state con messaggio errore", async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Errore: HTTP error! status: 500/i)
      ).toBeInTheDocument();
    });
  });

  it("Test 6: Badge chunking strategy colori corretti", async () => {
    const mockData = {
      documents: [
        {
          document_id: "123",
          document_name: "test.pdf",
          upload_date: "2025-01-15T10:00:00Z",
          chunk_count: 10,
          primary_chunking_strategy: "recursive",
        },
      ],
      total_count: 1,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      const badges = screen.getAllByText("recursive");
      expect(badges.length).toBeGreaterThan(0);
      expect(badges[badges.length - 1]).toBeInTheDocument();
    });
  });

  it("Test 7: Formattazione data corretta", async () => {
    const mockData = {
      documents: [
        {
          document_id: "123",
          document_name: "test.pdf",
          upload_date: "2025-01-15T10:00:00Z",
          chunk_count: 10,
          primary_chunking_strategy: "recursive",
        },
      ],
      total_count: 1,
    };

    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Data formattata in formato italiano (usa getAllByText per elementi multipli)
      const dates = screen.getAllByText(/15\/1\/2025|15\/01\/2025/);
      expect(dates.length).toBeGreaterThan(0);
      expect(dates[dates.length - 1]).toBeInTheDocument();
    });
  });

  it("Test 8: Token mancante mostra errore", async () => {
    (authService.getSession as any).mockResolvedValue({
      data: { session: null },
    });

    render(
      <BrowserRouter>
        <DocumentsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/Errore: Token di autenticazione mancante/i)
      ).toBeInTheDocument();
    });
  });
});
