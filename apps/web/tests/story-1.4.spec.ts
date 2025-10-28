import { test, expect } from "@playwright/test";

test.describe("Story 1.4 - Placeholder UI & Protected Routes", () => {
  test("routes exist and redirects for protected routes", async ({ page }) => {
    // Accesso diretto a rotta admin protetta → redirect a login
    await page.goto("/admin/dashboard");
    await expect(page).toHaveURL("/login");

    // Accesso diretto a rotta chat protetta → redirect a root
    await page.goto("/chat");
    await expect(page).toHaveURL("/");

    // La pagina di accesso è visibile
    await expect(page.getByRole("heading", { name: /Accesso Studente/i })).toBeVisible();
  });
});
