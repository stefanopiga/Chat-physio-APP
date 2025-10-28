import { test, expect } from "@playwright/test";

test.describe("Story 3.4 — Source Visualization & Feedback", () => {
  test("citazioni come bottoni e invio feedback", async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("chat.sessionId", "e2e-session-id");
      sessionStorage.setItem("temp_jwt", "e2e-temp-token");
    });

    await page.goto("/chat");

    // Attendi UI
    const input = page.getByPlaceholder("Inserisci la tua domanda...");
    await expect(input).toBeVisible({ timeout: 10000 });
    await input.fill("Che cos'è la lombalgia?");

    await page.route("**/api/v1/chat/query", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          chunks: [
            {
              id: "c1",
              document_id: "d1",
              content: "chunk1 contenuto...",
              similarity: 0.9,
            },
            {
              id: "c2",
              document_id: "d2",
              content: "chunk2 contenuto...",
              similarity: 0.85,
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/chat/sessions/*/messages", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          message_id: "m1",
          answer: "La lombalgia è...",
          citations: [
            {
              chunk_id: "c1",
              document_id: "d1",
              excerpt: "chunk1 contenuto...",
              position: 10,
            },
            {
              chunk_id: "c2",
              document_id: "d2",
              excerpt: "chunk2 contenuto...",
              position: 20,
            },
          ],
        }),
      });
    });

    await page.route("**/api/v1/chat/messages/*/feedback", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true }),
      });
    });

    // Invia
    const submitButton = page.getByRole("button", { name: "Invia" });
    await expect(submitButton).toBeEnabled();
    await submitButton.click();

    // Verifica citazioni visibili come bottoni
    await expect(page.getByRole("button", { name: /Fonte c1/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /Fonte c2/ })).toBeVisible();

    // Click su badge per popover
    await page.getByRole("button", { name: /Fonte c1/ }).click();
    await expect(page.getByRole("tooltip")).toBeVisible();
    await expect(page.getByText(/chunk1 contenuto/i)).toBeVisible();

    // Invio feedback 👍
    const up = page.getByRole("button", { name: "Vota positivo" });
    await up.click();
    await expect(up).toBeDisabled();
  });
});
