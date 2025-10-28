import {
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from "@testing-library/react";
import { describe, it, expect, beforeEach, afterAll, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import StudentTokensPage from "../StudentTokensPage";

const API_BASE_URL = "http://localhost:8000";

const mockSupabaseAuth = vi.hoisted(() => ({
  getSession: vi.fn(),
}));

vi.mock("../../lib/supabaseClient", () => ({
  supabase: {
    auth: mockSupabaseAuth,
  },
}));

const mockFetch = vi.fn();
global.fetch = mockFetch as unknown as typeof fetch;

const mockClipboard = { writeText: vi.fn() };
Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  writable: true,
});

const mockTokens = [
  {
    id: "token-1",
    first_name: "Mario",
    last_name: "Rossi",
    token: "8Jh3Kl9mPq2Rt5Vx7Yz0Ab4Cd6Ef8Gh1",
    is_active: true,
    expires_at: new Date(Date.now() + 86400000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: "token-2",
    first_name: "Luigi",
    last_name: "Verdi",
    token: "2Cd4Ef6Gh8Ij0Kl2Mn4Op6Qr8St0Uv2x",
    is_active: true,
    expires_at: new Date(Date.now() + 86400000 * 2).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

const mockGeneratedToken = {
  id: "token-new",
  token: "NewToken1234567890AbCdEfGh",
  first_name: "Nuovo",
  last_name: "Studente",
  expires_at: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubEnv("VITE_API_BASE_URL", API_BASE_URL);
  mockSupabaseAuth.getSession.mockResolvedValue({
    data: { session: { access_token: "mock-token" } },
    error: null,
  });
  mockFetch.mockResolvedValue({
    ok: true,
    json: async () => mockTokens,
  });
});

afterAll(() => {
  vi.unstubAllEnvs();
});

const renderPage = () =>
  render(
    <MemoryRouter>
      <StudentTokensPage />
    </MemoryRouter>
  );

describe("StudentTokensPage", () => {
  it("renders heading and toggle button", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: /gestione token studenti/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /mostra anche revocati/i })
    ).toBeInTheDocument();
  });

  it("fetches tokens using supabase access token", async () => {
    renderPage();

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    expect(mockFetch.mock.calls[0][0]).toBe(
      `${API_BASE_URL}/api/v1/admin/student-tokens?is_active=true`
    );
    const requestInit = mockFetch.mock.calls[0][1] as RequestInit;
    expect(requestInit?.headers).toMatchObject({
      Authorization: "Bearer mock-token",
    });
  });

  it("fetches inactive tokens when toggle is clicked", async () => {
    mockFetch.mockReset();
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          ...mockTokens,
          {
            ...mockTokens[0],
            id: "token-3",
            is_active: false,
          },
        ],
      });

    renderPage();

    const [toggleButton] = await screen.findAllByRole("button", {
      name: /mostra anche revocati/i,
    });
    fireEvent.click(toggleButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenLastCalledWith(
        `${API_BASE_URL}/api/v1/admin/student-tokens?is_active=`,
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
          }),
        })
      );
    });
  });

  it("submits form, generates token and allows copy", async () => {
    mockFetch.mockReset();
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockGeneratedToken,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [
          ...mockTokens,
          {
            ...mockTokens[0],
            id: "token-new",
            token: mockGeneratedToken.token,
          },
        ],
      });

    renderPage();

    const [firstNameInput] = screen.getAllByLabelText(/nome/i);
    fireEvent.change(firstNameInput, {
      target: { value: mockGeneratedToken.first_name },
    });
    const [lastNameInput] = screen.getAllByLabelText(/cognome/i);
    fireEvent.change(lastNameInput, {
      target: { value: mockGeneratedToken.last_name },
    });
    const [submitButton] = screen.getAllByRole("button", {
      name: /genera token/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(3));

    const postCall = mockFetch.mock.calls[1];
    const postRequest = postCall?.[1] as RequestInit | undefined;
    expect(postRequest?.method).toBe("POST");
    expect(postRequest?.headers).toMatchObject({
      Authorization: "Bearer mock-token",
      "Content-Type": "application/json",
    });

    expect(
      await screen.findByText(/Token generato con successo/i)
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /copia token/i }));
    expect(mockClipboard.writeText).toHaveBeenCalledWith(
      mockGeneratedToken.token
    );
  });

  it("revokes a token and refreshes the list", async () => {
    mockFetch.mockReset();
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockTokens,
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => ({}),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [mockTokens[1]],
      });

    renderPage();

    const [revokeButton] = await screen.findAllByRole("button", {
      name: /^revoca$/i,
    });
    fireEvent.click(revokeButton);

    const dialog = await screen.findByRole("dialog");
    const confirm = within(dialog).getByRole("button", { name: /^revoca$/i });
    fireEvent.click(confirm);

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(3));

    const deleteCall = mockFetch.mock.calls[1];
    expect(deleteCall[0]).toBe(
      `${API_BASE_URL}/api/v1/admin/student-tokens/token-1`
    );
    expect(deleteCall[1]).toMatchObject({
      method: "DELETE",
      headers: expect.objectContaining({
        Authorization: "Bearer mock-token",
      }),
    });
  });
});
