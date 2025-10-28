import { test, expect } from "@playwright/test";

test.describe("Story 4.1 - Admin Debug View", () => {
  test("admin autenticato naviga a /admin/debug e invia una query", async ({
    page,
  }) => {
    // ========== SETUP AUTH MOCK ==========
    await page.addInitScript(() => {
      /* eslint-disable @typescript-eslint/no-explicit-any */
      const mockSession = {
        access_token: "mock-admin-token",
        user: {
          id: "test-user-id",
          aud: "authenticated",
          role: "authenticated",
          email: "admin@test.com",
          app_metadata: { role: "admin" },
        },
      };

      // Mock authService per AdminGuard
      (window as any).__mockAuthService = {
        getSession: async () => ({
          data: { session: mockSession },
          error: null,
        }),
        onAuthStateChange: (callback: (event: string, s: any) => void) => {
          setTimeout(() => callback("SIGNED_IN", mockSession), 0);
          return {
            data: { subscription: { unsubscribe: () => {} } },
          };
        },
        isAdmin: () => true,
        isStudent: () => false,
        isAuthenticated: () => true,
      };

      // Token per apiClient.getAccessToken()
      sessionStorage.setItem("temp_jwt", "mock-admin-token");
      /* eslint-enable @typescript-eslint/no-explicit-any */
    });

    // Mock API backend response - registrato PRIMA della navigazione
    await page.route("**/api/v1/admin/debug/query", async (route) => {
      // Verifica che sia POST (best practice Playwright)
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          question: "Esempio domanda di test",
          answer: "Risposta di debug mockata",
          chunks: [
            {
              chunk_id: "chunk1",
              content: "Contenuto chunk 1",
              similarity_score: 0.95,
              metadata: {
                document_id: "doc1",
                document_name: "test.pdf",
                page_number: 1,
                chunking_strategy: "recursive",
              },
            },
          ],
          retrieval_time_ms: 100,
          generation_time_ms: 500,
        }),
      });
    });

    // ========== NAVIGAZIONE ==========
    await page.goto("/admin/debug");

    // Verifica che AdminGuard abbia concesso accesso
    await expect(
      page.getByRole("heading", { name: /Debug RAG/i })
    ).toBeVisible();

    // ========== INTERAZIONE UI ==========
    const textarea = page.locator("textarea#question");
    await textarea.fill("Esempio domanda di test");

    const submitButton = page.getByRole("button", {
      name: /Esegui Query Debug/i,
    });
    await submitButton.click();

    // ========== ASSERTIONS ==========
    // Verifica rendering risposta
    await expect(
      page.getByRole("heading", { name: /Risposta Finale/i })
    ).toBeVisible();

    await expect(page.getByText("Risposta di debug mockata")).toBeVisible();

    // Verifica rendering chunks
    await expect(page.getByText("Chunk Recuperati (1)")).toBeVisible();
    await expect(page.getByText("Score: 0.950")).toBeVisible();

    // Verifica timing metrics
    await expect(page.getByText(/Retrieval: 100ms/)).toBeVisible();
    await expect(page.getByText(/Generation: 500ms/)).toBeVisible();
  });

  test("utente non autenticato viene rediretto da /admin/debug", async ({
    page,
  }) => {
    // Mock authService senza sessione
    await page.addInitScript(() => {
      /* eslint-disable @typescript-eslint/no-explicit-any */
      (window as any).__mockAuthService = {
        getSession: async () => ({
          data: { session: null },
          error: null,
        }),
        onAuthStateChange: (callback: (event: string, s: any) => void) => {
          setTimeout(() => callback("SIGNED_OUT", null), 0);
          return {
            data: { subscription: { unsubscribe: () => {} } },
          };
        },
        isAdmin: () => false,
        isStudent: () => false,
        isAuthenticated: () => false,
      };
      /* eslint-enable @typescript-eslint/no-explicit-any */
    });

    await page.goto("/admin/debug");

    // Verifica redirect a login (comportamento di AdminGuard)
    await expect(page).toHaveURL("/login");
  });

  test("utente student (non admin) viene rediretto da /admin/debug", async ({
    page,
  }) => {
    // Mock authService con sessione student
    await page.addInitScript(() => {
      /* eslint-disable @typescript-eslint/no-explicit-any */
      const mockSession = {
        access_token: "mock-student-token",
        user: {
          id: "test-student-id",
          aud: "authenticated",
          role: "authenticated",
          email: "student@test.com",
          app_metadata: { role: "student" },
        },
      };

      (window as any).__mockAuthService = {
        getSession: async () => ({
          data: { session: mockSession },
          error: null,
        }),
        onAuthStateChange: (callback: (event: string, s: any) => void) => {
          setTimeout(() => callback("SIGNED_IN", mockSession), 0);
          return {
            data: { subscription: { unsubscribe: () => {} } },
          };
        },
        isAdmin: () => false,
        isStudent: () => true,
        isAuthenticated: () => true,
      };
      /* eslint-enable @typescript-eslint/no-explicit-any */
    });

    await page.goto("/admin/debug");

    // AdminGuard deve redirigere a login perché role !== "admin"
    await expect(page).toHaveURL("/login");
  });
});
