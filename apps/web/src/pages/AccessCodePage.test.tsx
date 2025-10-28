import React from "react";
import "@testing-library/jest-dom/vitest";
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type Mock,
} from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import AccessCodePage from "./AccessCodePage";

// Mock react-router-dom useNavigate with a stable spy per test
let navigateMock: ReturnType<typeof vi.fn>;
vi.mock("react-router-dom", async () => {
  const mod = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom"
  );
  return {
    ...mod,
    useNavigate: () => navigateMock,
  };
});

describe("AccessCodePage", () => {
  const originalFetch = globalThis.fetch as typeof fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
    globalThis.fetch = vi.fn() as unknown as typeof fetch;
    sessionStorage.clear();
    navigateMock = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    cleanup();
  });

  it("renders input field", () => {
    render(<AccessCodePage />);
    expect(screen.getByLabelText(/Codice di accesso/i)).toBeInTheDocument();
  });

  it("shows error when submitting empty code", () => {
    render(<AccessCodePage />);
    const submitBtn = screen.getAllByRole("button", { name: /Entra/i })[0];
    fireEvent.submit(submitBtn.closest("form") as HTMLFormElement);
    expect(screen.getByText(/non può essere vuoto/i)).toBeInTheDocument();
  });

  it("redirects to /chat on valid code", async () => {
    (globalThis.fetch as unknown as Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ token: "t", token_type: "bearer", expires_in: 900 }),
    });

    render(<AccessCodePage />);

    fireEvent.change(screen.getByLabelText(/Codice di accesso/i), {
      target: { value: "ABC123" },
    });
    const submitBtn = screen.getAllByRole("button", { name: /Entra/i })[0];
    fireEvent.submit(submitBtn.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(sessionStorage.getItem("temp_jwt")).toBe("t");
      expect(navigateMock).toHaveBeenCalledWith("/chat");
    });
  });

  it("shows API error message on invalid code", async () => {
    (globalThis.fetch as unknown as Mock).mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: async () => "invalid_code",
    });

    render(<AccessCodePage />);
    fireEvent.change(screen.getByLabelText(/Codice di accesso/i), {
      target: { value: "BAD" },
    });
    const submitBtn = screen.getAllByRole("button", { name: /Entra/i })[0];
    fireEvent.submit(submitBtn.closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(screen.getByText(/invalid_code/i)).toBeInTheDocument();
    });
  });
});
