import { test, expect } from "@playwright/test";

test.describe("Story 1.3: Student Access Code System", () => {
  test.beforeEach(async ({ page }) => {
    // La pagina di accesso è la root in questo setup
    await page.goto("/");
  });

  // Test Design: TD-E1 (Client-side validation)
  test("TD-E1: blocca l invio e mostra errore se il codice è vuoto", async ({
    page,
  }) => {
    // Attendi elementi chiave
    await expect(page.getByPlaceholder(/inserisci il codice/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /entra/i })).toBeVisible();

    // Clicca il pulsante di invio senza inserire un codice
    await page.getByRole("button", { name: /entra/i }).click();

    // Verifica che la navigazione non sia avvenuta
    await expect(page).toHaveURL("/");

    // Verifica la presenza del messaggio di errore specifico per campo vuoto
    await expect(
      page.locator("text=Il campo codice non può essere vuoto.")
    ).toBeVisible();
  });

  // Test Design: TD-E2 (Valid code redirect)
  test("TD-E2: reindirizza a /chat con un codice valido", async ({ page }) => {
    // Attendi elementi chiave
    await expect(page.getByPlaceholder(/inserisci il codice/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /entra/i })).toBeVisible();

    // Intercetta e mocka la risposta API per un codice valido
    await page.route("**/api/v1/auth/exchange-code", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          token: "fake-jwt-token-for-testing",
          token_type: "bearer",
          expires_in: 900,
        }),
      });
    });

    // Inserisci un codice nel campo di input
    await page.getByPlaceholder(/inserisci il codice/i).fill("VALIDCODE");

    // Clicca il pulsante di invio
    await page.getByRole("button", { name: /entra/i }).click();

    // Attendi e verifica il reindirizzamento alla pagina /chat
    await page.waitForURL("/chat");
    await expect(page).toHaveURL("/chat");

    // Verifica che il token sia stato salvato in sessionStorage
    const token = await page.evaluate(() => sessionStorage.getItem("temp_jwt"));
    expect(token).toBe("fake-jwt-token-for-testing");
  });

  // Test Design: TD-E3 (API error surfaced to user)
  test("TD-E3: mostra un messaggio di errore dall API per codice non valido", async ({
    page,
  }) => {
    // Attendi elementi chiave
    await expect(page.getByPlaceholder(/inserisci il codice/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /entra/i })).toBeVisible();

    const errorMessage = "Codice non valido o scaduto.";

    // Intercetta e mocka la risposta API per un codice non valido
    await page.route("**/api/v1/auth/exchange-code", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "text/plain",
        body: errorMessage,
      });
    });

    // Inserisci un codice non valido
    await page.getByPlaceholder(/inserisci il codice/i).fill("INVALIDCODE");

    // Clicca il pulsante di invio
    await page.getByRole("button", { name: /entra/i }).click();

    // Verifica che la navigazione non sia avvenuta
    await expect(page).toHaveURL("/");

    // Verifica la presenza del messaggio di errore proveniente dall'API
    await expect(page.locator(`text=${errorMessage}`)).toBeVisible();
  });
});
