import { test, expect } from "@playwright/test";

test.describe("Story 2.11 - Chat RAG End-to-End", () => {
  test.beforeEach(async ({ page }) => {
    // Setup auth mock per student role
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

      sessionStorage.setItem("temp_jwt", "mock-student-token");
      localStorage.setItem("chat.sessionId", "test-session-123");
      /* eslint-enable @typescript-eslint/no-explicit-any */
    });
  });

  test("AC2, AC5: Happy path - invia domanda, riceve risposta con citazioni", async ({
    page,
  }) => {
    // Mock API response con citazioni valide
    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      // Delay per rendere visibile il loading indicator
      await new Promise((resolve) => setTimeout(resolve, 100));

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: "msg-001",
          message:
            "La radicolopatia lombare e cervicale differiscono per la localizzazione dei sintomi.",
          answer:
            "La radicolopatia lombare e cervicale differiscono per la localizzazione dei sintomi.",
          citations: [
            {
              chunk_id: "chunk-001",
              document_id: "doc-radicolopatia-lombare",
              excerpt:
                "La radicolopatia lombare causa sintomi agli arti inferiori...",
              position: 1,
            },
            {
              chunk_id: "chunk-002",
              document_id: "doc-radicolopatia-cervicale",
              excerpt:
                "La radicolopatia cervicale causa sintomi agli arti superiori...",
              position: 2,
            },
          ],
          retrieval_time_ms: 450,
          generation_time_ms: 2300,
        }),
      });
    });

    await page.goto("/chat");

    // Verifica UI iniziale
    await expect(page.locator("h1")).toContainText("Chat");
    await expect(page.getByTestId("chat-messages-container")).toBeVisible();

    // Invia domanda
    const input = page.getByTestId("chat-input-field");
    await input.fill(
      "Qual è la differenza tra radicolopatia lombare e cervicale?"
    );

    const submitBtn = page.getByTestId("chat-submit-button");
    await submitBtn.click();

    // Verifica stato loading (con timeout breve perché potrebbe essere veloce)
    await expect(page.getByTestId("chat-loading-indicator")).toBeVisible({
      timeout: 1000,
    });
    await expect(submitBtn).toBeDisabled();

    // Attendi risposta
    await expect(page.getByTestId("chat-loading-indicator")).not.toBeVisible({
      timeout: 10000,
    });

    // Verifica messaggio utente
    const userMessages = page.getByTestId("chat-message-user");
    await expect(userMessages).toHaveCount(1);
    await expect(userMessages.first()).toContainText("radicolopatia lombare");

    // Verifica risposta assistant con citazioni
    const assistantMessages = page.getByTestId("chat-message-assistant");
    await expect(assistantMessages).toHaveCount(1);
    await expect(assistantMessages.first()).toContainText(
      "radicolopatia lombare e cervicale differiscono"
    );

    // Verifica presenza citazioni
    const citations = page.getByTestId("message-citations");
    await expect(citations).toBeVisible();

    const citationBadges = page.locator('[data-testid^="citation-badge-"]');
    await expect(citationBadges).toHaveCount(2);

    // Verifica input form è riabilitato (ma submit disabled perché input vuoto)
    await expect(input).toBeEnabled();
    await expect(input).toHaveValue(""); // Input svuotato dopo submit
    await expect(submitBtn).toBeDisabled(); // Disabled perché input vuoto

    // Verifica che digitando di nuovo si riabilita
    await input.fill("Altra domanda");
    await expect(submitBtn).toBeEnabled();
  });

  test("AC2: Citation popover - click su badge mostra dettagli", async ({
    page,
  }) => {
    // Mock API response
    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: "msg-002",
          message: "Risposta di test con citazione.",
          citations: [
            {
              chunk_id: "chunk-test-001",
              document_id: "doc-test-001",
              excerpt: "Questo è un estratto del documento fonte di esempio.",
              position: 1,
            },
          ],
        }),
      });
    });

    await page.goto("/chat");

    // Invia domanda
    await page.getByTestId("chat-input-field").fill("Domanda di test");
    await page.getByTestId("chat-submit-button").click();

    // Attendi risposta
    await expect(page.getByTestId("chat-message-assistant")).toBeVisible({
      timeout: 10000,
    });

    // Click su citation badge
    const citationBadge = page.getByTestId("citation-badge-chunk-test-001");
    await expect(citationBadge).toBeVisible();
    await citationBadge.click();

    // Verifica popover visibile con contenuto
    const popover = page.getByTestId("citation-popover");
    await expect(popover).toBeVisible();
    await expect(page.getByTestId("popover-document-id")).toContainText(
      "doc-test-001"
    );
    await expect(page.getByTestId("popover-excerpt")).toContainText(
      "estratto del documento fonte"
    );
  });

  test("AC2: Error handling - 429 Rate Limit", async ({ page }) => {
    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      await route.fulfill({
        status: 429,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Rate limit exceeded" }),
      });
    });

    await page.goto("/chat");

    await page.getByTestId("chat-input-field").fill("Test rate limit");
    await page.getByTestId("chat-submit-button").click();

    // Verifica messaggio errore 429
    const errorMessage = page.getByTestId("chat-error-message");
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    await expect(errorMessage).toContainText(
      "Hai superato il limite di richieste"
    );

    // Verifica loading non più visibile
    await expect(page.getByTestId("chat-loading-indicator")).not.toBeVisible();

    // Verifica nessun messaggio assistant aggiunto
    await expect(page.getByTestId("chat-message-assistant")).toHaveCount(0);
  });

  test("AC2: Error handling - 500 Generic Error", async ({ page }) => {
    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      // Delay per simulare latenza
      await new Promise((resolve) => setTimeout(resolve, 50));

      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Internal server error" }),
      });
    });

    await page.goto("/chat");

    const input = page.getByTestId("chat-input-field");
    const submitBtn = page.getByTestId("chat-submit-button");

    await input.fill("Test server error");
    await submitBtn.click();

    // Verifica messaggio errore generico
    const errorMessage = page.getByTestId("chat-error-message");
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    await expect(errorMessage).toContainText(
      "Si è verificato un errore. Riprova"
    );

    // Verifica form riabilitato per retry (ma submit disabled perché input vuoto)
    await expect(input).toBeEnabled();
    await expect(input).toHaveValue(""); // Input svuotato dopo submit
    await expect(submitBtn).toBeDisabled(); // Disabled perché input vuoto

    // Verifica che digitando di nuovo si può riprovare
    await input.fill("Retry dopo errore");
    await expect(submitBtn).toBeEnabled();
  });

  test("AC2: Error handling - Timeout simulato", async ({ page }) => {
    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      // Simula timeout (non risponde)
      await new Promise((resolve) => setTimeout(resolve, 15000));
      await route.fulfill({
        status: 504,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Gateway Timeout" }),
      });
    });

    await page.goto("/chat");

    await page.getByTestId("chat-input-field").fill("Test timeout");
    await page.getByTestId("chat-submit-button").click();

    // Verifica messaggio errore dopo timeout
    const errorMessage = page.getByTestId("chat-error-message");
    await expect(errorMessage).toBeVisible({ timeout: 20000 });
    await expect(errorMessage).toContainText(
      "Si è verificato un errore. Riprova"
    );
  });

  test("AC2, AC5: Stati loading corretti durante invio", async ({ page }) => {
    let resolveRequest: (value: unknown) => void;
    const requestPromise = new Promise((resolve) => {
      resolveRequest = resolve;
    });

    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      // Attendi risoluzione manuale per controllare timing
      await requestPromise;

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: "msg-003",
          message: "Risposta dopo loading.",
          citations: [],
        }),
      });
    });

    await page.goto("/chat");

    const input = page.getByTestId("chat-input-field");
    const submitBtn = page.getByTestId("chat-submit-button");

    await input.fill("Test loading states");
    await submitBtn.click();

    // Verifica loading indicator visibile
    await expect(page.getByTestId("chat-loading-indicator")).toBeVisible();

    // Verifica submit button disabilitato
    await expect(submitBtn).toBeDisabled();

    // Verifica input disabilitato
    await expect(input).toBeDisabled();

    // Risolvi la richiesta
    resolveRequest!(null);

    // Verifica loading scompare
    await expect(page.getByTestId("chat-loading-indicator")).not.toBeVisible({
      timeout: 10000,
    });

    // Verifica form riabilitato (input enabled, submit disabled perché input vuoto)
    await expect(input).toBeEnabled();
    await expect(input).toHaveValue(""); // Input svuotato
    await expect(submitBtn).toBeDisabled(); // Disabled perché input vuoto

    // Verifica che digitando si riabilita
    await input.fill("Nuovo messaggio");
    await expect(submitBtn).toBeEnabled();
  });

  test("AC5: Validazione flusso completo - sequenza di domande", async ({
    page,
  }) => {
    let callCount = 0;

    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      if (route.request().method() !== "POST") {
        await route.continue();
        return;
      }

      callCount++;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: `msg-${callCount}`,
          message: `Risposta numero ${callCount}.`,
          citations:
            callCount === 2
              ? [
                  {
                    chunk_id: `chunk-${callCount}`,
                    document_id: `doc-${callCount}`,
                    excerpt: `Estratto per domanda ${callCount}`,
                    position: callCount,
                  },
                ]
              : [],
        }),
      });
    });

    await page.goto("/chat");

    // Prima domanda
    await page.getByTestId("chat-input-field").fill("Prima domanda");
    await page.getByTestId("chat-submit-button").click();
    await expect(page.getByTestId("chat-message-assistant")).toHaveCount(1, {
      timeout: 10000,
    });

    // Seconda domanda con citazioni
    await page.getByTestId("chat-input-field").fill("Seconda domanda");
    await page.getByTestId("chat-submit-button").click();
    await expect(page.getByTestId("chat-message-assistant")).toHaveCount(2, {
      timeout: 10000,
    });

    // Verifica citazioni sulla seconda risposta
    const citations = page.getByTestId("message-citations");
    await expect(citations).toBeVisible();

    // Terza domanda
    await page.getByTestId("chat-input-field").fill("Terza domanda");
    await page.getByTestId("chat-submit-button").click();
    await expect(page.getByTestId("chat-message-assistant")).toHaveCount(3, {
      timeout: 10000,
    });

    // Verifica tutti i messaggi utente
    await expect(page.getByTestId("chat-message-user")).toHaveCount(3);

    // Verifica che le risposte precedenti siano ancora visibili
    const assistantMessages = page.getByTestId("chat-message-assistant");
    await expect(assistantMessages.nth(0)).toContainText("Risposta numero 1");
    await expect(assistantMessages.nth(1)).toContainText("Risposta numero 2");
    await expect(assistantMessages.nth(2)).toContainText("Risposta numero 3");
  });
});
