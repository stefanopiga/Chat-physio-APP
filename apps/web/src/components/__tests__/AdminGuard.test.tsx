import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import AdminGuard from "../AdminGuard";
import { authService } from "../../services/authService";
import type { Session } from "@supabase/supabase-js";

// Mock del servizio di autenticazione
vi.mock("../../services/authService", () => ({
  authService: {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    isAdmin: vi.fn(),
  },
}));

// Mock di react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("AdminGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("mostra loading durante verifica autenticazione", () => {
    const mockUnsubscribe = vi.fn();
    vi.mocked(authService.getSession).mockReturnValue(
      new Promise(() => {}) // Promise non risolta
    );
    vi.mocked(authService.onAuthStateChange).mockReturnValue({
      data: {
        subscription: {
          unsubscribe: mockUnsubscribe,
        },
      },
    });

    render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    expect(
      screen.getByText("Verifica autorizzazione amministratore...")
    ).toBeInTheDocument();
  });

  it("renderizza children quando sessione admin valida", async () => {
    const mockSession: Session = {
      access_token: "test-token",
      token_type: "bearer",
      expires_in: 3600,
      expires_at: Date.now() / 1000 + 3600,
      refresh_token: "test-refresh",
      user: {
        id: "test-user-id",
        aud: "authenticated",
        role: "authenticated",
        email: "admin@test.com",
        app_metadata: { role: "admin" },
        user_metadata: {},
        created_at: new Date().toISOString(),
      },
    };

    const mockUnsubscribe = vi.fn();

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    vi.mocked(authService.onAuthStateChange).mockImplementation((callback) => {
      setTimeout(() => callback("SIGNED_IN", mockSession), 0);
      return {
        data: {
          subscription: {
            unsubscribe: mockUnsubscribe,
          },
        },
      };
    });

    vi.mocked(authService.isAdmin).mockReturnValue(true);

    render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    expect(authService.getSession).toHaveBeenCalled();
    expect(authService.isAdmin).toHaveBeenCalledWith(mockSession);
  });

  it("redirige a home quando sessione non esiste", async () => {
    const mockUnsubscribe = vi.fn();

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    });

    vi.mocked(authService.onAuthStateChange).mockImplementation((callback) => {
      setTimeout(() => callback("SIGNED_OUT", null), 0);
      return {
        data: {
          subscription: {
            unsubscribe: mockUnsubscribe,
          },
        },
      };
    });

    vi.mocked(authService.isAdmin).mockReturnValue(false);

    const { container } = render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });

    expect(container.querySelector("[children]")).toBeNull();
  });

  it("redirige a home quando utente non è admin", async () => {
    const mockSession: Session = {
      access_token: "test-token",
      token_type: "bearer",
      expires_in: 3600,
      expires_at: Date.now() / 1000 + 3600,
      refresh_token: "test-refresh",
      user: {
        id: "test-user-id",
        aud: "authenticated",
        role: "authenticated",
        email: "student@test.com",
        app_metadata: { role: "student" },
        user_metadata: {},
        created_at: new Date().toISOString(),
      },
    };

    const mockUnsubscribe = vi.fn();

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    vi.mocked(authService.onAuthStateChange).mockImplementation((callback) => {
      setTimeout(() => callback("SIGNED_IN", mockSession), 0);
      return {
        data: {
          subscription: {
            unsubscribe: mockUnsubscribe,
          },
        },
      };
    });

    vi.mocked(authService.isAdmin).mockReturnValue(false);

    render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });

    expect(
      screen.queryByText("Verifica autorizzazione amministratore...")
    ).toBeInTheDocument();
  });

  it("cleanup subscription al unmount", async () => {
    const mockUnsubscribe = vi.fn();
    const mockSession: Session = {
      access_token: "test-token",
      token_type: "bearer",
      expires_in: 3600,
      expires_at: Date.now() / 1000 + 3600,
      refresh_token: "test-refresh",
      user: {
        id: "test-user-id",
        aud: "authenticated",
        role: "authenticated",
        email: "admin@test.com",
        app_metadata: { role: "admin" },
        user_metadata: {},
        created_at: new Date().toISOString(),
      },
    };

    vi.mocked(authService.getSession).mockResolvedValue({
      data: { session: mockSession },
      error: null,
    });

    vi.mocked(authService.onAuthStateChange).mockImplementation((callback) => {
      setTimeout(() => callback("SIGNED_IN", mockSession), 0);
      return {
        data: {
          subscription: {
            unsubscribe: mockUnsubscribe,
          },
        },
      };
    });

    vi.mocked(authService.isAdmin).mockReturnValue(true);

    const { unmount } = render(
      <BrowserRouter>
        <AdminGuard>
          <div>Protected Content</div>
        </AdminGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});
