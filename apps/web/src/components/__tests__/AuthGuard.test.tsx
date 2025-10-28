import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import AuthGuard from "../AuthGuard";
import { authService } from "../../services/authService";
import type { Session } from "@supabase/supabase-js";

// Mock del servizio di autenticazione
vi.mock("../../services/authService", () => ({
  authService: {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    isAuthenticated: vi.fn(),
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

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, "sessionStorage", {
  value: sessionStorageMock,
});

describe("AuthGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorageMock.clear();
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
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </BrowserRouter>
    );

    expect(screen.getByText("Verifica autenticazione...")).toBeInTheDocument();
  });

  it("renderizza children quando sessione autenticata valida", async () => {
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

    vi.mocked(authService.isAuthenticated).mockReturnValue(true);

    render(
      <BrowserRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    expect(authService.getSession).toHaveBeenCalled();
  });

  it("renderizza children quando temp_jwt presente in sessionStorage", async () => {
    sessionStorageMock.setItem("temp_jwt", "temp-token-value");

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

    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    render(
      <BrowserRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });
  });

  it("redirige a home quando nessuna sessione e nessun temp_jwt", async () => {
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

    vi.mocked(authService.isAuthenticated).mockReturnValue(false);

    render(
      <BrowserRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });

    expect(
      screen.queryByText("Verifica autenticazione...")
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
        email: "student@test.com",
        app_metadata: { role: "student" },
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

    vi.mocked(authService.isAuthenticated).mockReturnValue(true);

    const { unmount } = render(
      <BrowserRouter>
        <AuthGuard>
          <div>Protected Content</div>
        </AuthGuard>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Protected Content")).toBeInTheDocument();
    });

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});
