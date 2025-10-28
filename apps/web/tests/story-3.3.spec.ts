import { test, expect } from "@playwright/test";

// Nota: test E2E basico. Richiede backend accessibile e auth mockata o sessione valida.
// Per ambiente locale potrebbe necessitare setup aggiuntivo non incluso qui.

test.describe("Story 3.3 — Frontend Chat Integration", () => {
  test("UI invia domanda, mostra loader e visualizza risposta", async ({
    page,
  }) => {
    // Preimposta sessione e sessionId prima del caricamento della pagina
    await page.addInitScript(() => {
      /* eslint-disable @typescript-eslint/no-explicit-any */
      localStorage.setItem("chat.sessionId", "e2e-session-id");
      sessionStorage.setItem("temp_jwt", "e2e-temp-token");

      // Mock authService per AuthGuard
      const mockSession = {
        access_token: "e2e-temp-token",
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

    await page.goto("/chat");

    // Attendi sblocco AuthGuard prima di interagire
    await expect(
      page.getByText("Verifica autenticazione...")
    ).not.toBeVisible();

    // Usa selettore robusto e attesa esplicita
    const input = page.getByPlaceholder("Inserisci la tua domanda...");
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("Che cos'è la lombalgia?");

    // Intercetta chiamate API e fornisci risposte mockate
    await page.route("**/api/v1/chat/query", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          chunks: [
            { id: "c1", document_id: "d1", content: "chunk1", similarity: 0.9 },
            {
              id: "c2",
              document_id: "d2",
              content: "chunk2",
              similarity: 0.85,
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      // Delay artificiale per dare tempo al loader di apparire
      await new Promise(resolve => setTimeout(resolve, 200));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          answer: "La lombalgia è un dolore nella parte bassa della schiena.",
        }),
      });
    });

    // Invio (attendi che il bottone sia abilitato)
    const submitButton = page.getByRole("button", { name: "Invia" });
    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    // Verifica loader (con timeout breve, può apparire rapidamente)
    await expect(page.getByText("Caricamento...")).toBeVisible({ timeout: 2000 });

    // Verifica risposta renderizzata
    await expect(
      page.getByText(
        "La lombalgia è un dolore nella parte bassa della schiena."
      )
    ).toBeVisible();
  });
});
