import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AuthGuard from "../../components/AuthGuard";

vi.mock("../../lib/supabaseClient", () => ({
  supabase: {
    auth: {
      onAuthStateChange: () => ({
        data: { subscription: { unsubscribe: () => {} } },
      }),
      getSession: async () => ({ data: { session: null } }),
    },
  },
}));

describe("AuthGuard", () => {
  it("redirects when not authenticated", async () => {
    const { findByText } = render(
      <MemoryRouter initialEntries={["/chat"]}>
        <AuthGuard>
          <div>Protected</div>
        </AuthGuard>
      </MemoryRouter>
    );

    expect(await findByText(/Verifica autenticazione/i)).toBeDefined();
  });
});
