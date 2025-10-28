import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import AdminGuard from "../../components/AdminGuard";

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

describe("AdminGuard", () => {
  it("redirects non-admin or unauthenticated", async () => {
    const { findByText } = render(
      <MemoryRouter initialEntries={["/admin/dashboard"]}>
        <AdminGuard>
          <div>Admin Protected</div>
        </AdminGuard>
      </MemoryRouter>
    );

    expect(
      await findByText(/Verifica autorizzazione amministratore/i)
    ).toBeDefined();
  });
});
