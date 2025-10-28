import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import DashboardPage from "../DashboardPage";
import { authService } from "@/services/authService";
import type { Session } from "@supabase/supabase-js";

vi.mock("@/services/authService", () => ({
  authService: {
    getSession: vi.fn(),
  },
}));

const mockAdminSession: Session = {
  access_token: "mock-token",
  refresh_token: "mock-refresh",
  expires_in: 3600,
  expires_at: Date.now() / 1000 + 3600,
  token_type: "bearer",
  user: {
    id: "mock-admin-id",
    email: "admin@test.com",
    app_metadata: { role: "admin" },
    user_metadata: {},
    aud: "authenticated",
    created_at: new Date().toISOString(),
  },
};

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders heading Dashboard Amministratore", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /dashboard amministratore/i })
      ).toBeInTheDocument();
    });
  });

  it("displays admin email from session", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/benvenuto, admin@test.com/i)
      ).toBeInTheDocument();
    });
  });

  it("displays fallback when session is null", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/benvenuto, amministratore/i)
      ).toBeInTheDocument();
    });
  });

  it("displays fallback when email is undefined", async () => {
    const sessionWithoutEmail: Session = {
      ...mockAdminSession,
      user: {
        ...mockAdminSession.user,
        email: undefined,
      },
    };

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: sessionWithoutEmail },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(
        screen.getByText(/benvenuto, amministratore/i)
      ).toBeInTheDocument();
    });
  });

  it("has correct href for Debug RAG card", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      const debugLinks = screen.getAllByRole("link", {
        name: /vai a debug rag/i,
      });
      expect(debugLinks.length).toBeGreaterThan(0);
      expect(debugLinks[0]).toHaveAttribute("href", "/admin/debug");
    });
  });

  it("Analytics card is navigable (Story 4.2 - no Coming Soon)", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      const analyticsLinks = screen.getAllByRole("link", {
        name: /vai a analytics dashboard/i,
      });
      expect(analyticsLinks.length).toBeGreaterThan(0);
      expect(analyticsLinks[0]).toHaveAttribute("href", "/admin/analytics");
      // Verifica che NON ci sia badge "Coming Soon"
      expect(screen.queryByText(/coming soon/i)).not.toBeInTheDocument();
    });
  });

  it("has aria-label for accessibility on Debug RAG link", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      const debugLinks = screen.getAllByRole("link", {
        name: /vai a debug rag/i,
      });
      expect(debugLinks.length).toBeGreaterThan(0);
      expect(debugLinks[0]).toHaveAttribute("aria-label", "Vai a Debug RAG");
    });
  });

  it("has responsive grid classes", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    const { container } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      const gridContainer = container.querySelector(".grid");
      expect(gridContainer).toHaveClass("grid-cols-1");
      expect(gridContainer).toHaveClass("md:grid-cols-2");
      expect(gridContainer).toHaveClass("gap-4");
    });
  });

  it("Analytics card is clickable and enabled (Story 4.2)", async () => {
    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockAdminSession },
      error: null,
    });

    const { container } = render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      const analyticsLinks = screen.getAllByRole("link", {
        name: /vai a analytics dashboard/i,
      });
      expect(analyticsLinks.length).toBeGreaterThan(0);
      expect(analyticsLinks[0]).toHaveAttribute("href", "/admin/analytics");

      // Verifica che NON abbia classi disabled cercando nel container
      const cards = container.querySelectorAll('[data-slot="card"]');
      const analyticsCard = Array.from(cards).find((card) =>
        card.textContent?.includes("Analytics Dashboard")
      );
      expect(analyticsCard).toBeDefined();
      expect(analyticsCard).not.toHaveClass("cursor-not-allowed");
      expect(analyticsCard).not.toHaveClass("opacity-60");
    });
  });

  it("shows loading state initially", () => {
    vi.mocked(authService.getSession).mockImplementation(
      () =>
        new Promise(() => {
          // Never resolves to keep loading state
        })
    );

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    );

    expect(
      screen.getByText(/caricamento dashboard\.\.\./i)
    ).toBeInTheDocument();
  });
});
