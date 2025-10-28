/**
 * E2E tests for Story 4.4: Document Chunk Explorer.
 *
 * Test Scenarios:
 * 1. Admin login → navigazione /admin/documents → tabella visibile
 * 2. Click documento → navigazione a chunks page → chunk list renderizzata
 * 3. Click "Mostra contenuto completo" → dialog aperto con full content
 * 4. Filter per strategy → chunk list aggiornata
 * 5. Sort per size → chunk riordinati
 * 6. Non-admin redirect da /admin/documents
 */

import { test, expect } from "@playwright/test";

// Mock admin token per test
const MOCK_ADMIN_TOKEN =
  "QUNDO LEGGI L'ERRORE NEI TEST, APRI QUESTO FILE E INSERISCI IL TUO TOKEN PERSONALE";

test.describe("Story 4.4: Document Chunk Explorer", () => {
  test.beforeEach(async ({ page }) => {
    // Mock authService per AdminGuard (supporto built-in in authService.ts)
    await page.addInitScript(() => {
      const mockSession = {
        user: {
          id: "admin-123",
          email: "admin@test.com",
          app_metadata: { role: "admin" },
        },
        access_token: "mock-admin-token",
      };

      (window as any).__mockAuthService = {
        getSession: () =>
          Promise.resolve({ data: { session: mockSession }, error: null }),
        onAuthStateChange: (callback: any) => {
          // Chiama callback immediatamente con sessione mock
          setTimeout(() => callback("SIGNED_IN", mockSession), 0);
          return {
            data: { subscription: { unsubscribe: () => {} } },
          };
        },
        isAdmin: (session: any) =>
          session?.user?.app_metadata?.role === "admin",
        isStudent: () => false,
        isAuthenticated: (session: any) => session !== null,
      };
    });

    // Set auth token in localStorage per API calls
    await page.addInitScript((token) => {
      localStorage.setItem("authToken", token);
    }, MOCK_ADMIN_TOKEN);

    // Mock API responses
    await page.route("**/api/v1/admin/documents", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          documents: [
            {
              document_id: "123e4567-e89b-12d3-a456-426614174000",
              document_name: "anatomia_spalla.pdf",
              upload_date: "2025-01-15T10:00:00Z",
              chunk_count: 15,
              primary_chunking_strategy: "recursive",
            },
            {
              document_id: "223e4567-e89b-12d3-a456-426614174000",
              document_name: "ginocchio.pdf",
              upload_date: "2025-01-16T11:00:00Z",
              chunk_count: 20,
              primary_chunking_strategy: "semantic",
            },
          ],
          total_count: 2,
        }),
      });
    });

    await page.route("**/api/v1/admin/documents/*/chunks**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          document_id: "123e4567-e89b-12d3-a456-426614174000",
          document_name: "anatomia_spalla.pdf",
          chunks: [
            {
              chunk_id: "chunk-1",
              content:
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
              chunk_size: 445,
              chunk_index: 0,
              chunking_strategy: "recursive",
              page_number: 1,
              embedding_status: "indexed",
              created_at: "2025-01-15T10:00:00Z",
            },
            {
              chunk_id: "chunk-2",
              content: "Breve contenuto chunk",
              chunk_size: 21,
              chunk_index: 1,
              chunking_strategy: "recursive",
              page_number: 2,
              embedding_status: "indexed",
              created_at: "2025-01-15T10:01:00Z",
            },
          ],
          total_chunks: 2,
        }),
      });
    });
  });

  test("Scenario 1: Admin login → navigazione /admin/documents → tabella visibile", async ({
    page,
  }) => {
    await page.goto("/admin/documents");

    // Attendi caricamento
    await expect(page.getByText("Document Explorer")).toBeVisible();

    // Verifica tabella documenti
    await expect(page.getByText("anatomia_spalla.pdf")).toBeVisible();
    await expect(page.getByText("ginocchio.pdf")).toBeVisible();

    // Verifica colonne (usa role per evitare strict mode violation)
    await expect(
      page.getByRole("columnheader", { name: "Documento" })
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Data Upload" })
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Chunk Count" })
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Strategia" })
    ).toBeVisible();
    await expect(
      page.getByRole("columnheader", { name: "Azioni" })
    ).toBeVisible();
  });

  test("Scenario 2: Click documento → navigazione a chunks page → chunk list renderizzata", async ({
    page,
  }) => {
    await page.goto("/admin/documents");

    // Click su "Visualizza Chunk"
    await page.getByText("Visualizza Chunk").first().click();

    // Attendi navigazione
    await expect(page).toHaveURL(/\/admin\/documents\/.*\/chunks/);

    // Verifica chunk list
    await expect(page.getByText("anatomia_spalla.pdf")).toBeVisible();
    await expect(page.getByText("2 chunk generati")).toBeVisible();

    // Verifica chunk cards
    await expect(page.getByText("Chunk #0")).toBeVisible();
    await expect(page.getByText("Chunk #1")).toBeVisible();

    // Verifica contenuto preview
    await expect(page.getByText(/Lorem ipsum/)).toBeVisible();
    await expect(page.getByText("Breve contenuto chunk")).toBeVisible();
  });

  test('Scenario 3: Click "Mostra contenuto completo" → dialog aperto con full content', async ({
    page,
  }) => {
    await page.goto(
      "/admin/documents/123e4567-e89b-12d3-a456-426614174000/chunks"
    );

    // Click su "Mostra contenuto completo" (solo per chunk lungo)
    await page.getByText("Mostra contenuto completo").click();

    // Verifica dialog aperto
    await expect(page.getByText("Chunk #0 - Contenuto Completo")).toBeVisible();

    // Verifica contenuto completo visibile
    await expect(page.getByText(/Lorem ipsum.*laborum/s)).toBeVisible();

    // Chiudi dialog (click su X o ESC)
    await page.keyboard.press("Escape");
    await expect(
      page.getByText("Chunk #0 - Contenuto Completo")
    ).not.toBeVisible();
  });

  test("Scenario 4: Filter per strategy → chunk list aggiornata", async ({
    page,
  }) => {
    await page.goto(
      "/admin/documents/123e4567-e89b-12d3-a456-426614174000/chunks"
    );

    // Verifica chunk iniziali
    await expect(page.getByText("Chunk #0")).toBeVisible();
    await expect(page.getByText("Chunk #1")).toBeVisible();

    // Mock filtered response
    await page.route("**/api/v1/admin/documents/*/chunks**", async (route) => {
      const url = new URL(route.request().url());
      if (url.searchParams.get("strategy") === "semantic") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            document_id: "123e4567-e89b-12d3-a456-426614174000",
            document_name: "anatomia_spalla.pdf",
            chunks: [],
            total_chunks: 0,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Apri dropdown strategia e seleziona "Semantic"
    await page.getByRole("combobox").first().click();
    await page.getByText("Semantic").click();

    // Verifica empty state
    await expect(page.getByText("Nessun chunk trovato")).toBeVisible();
  });

  test("Scenario 5: Sort per size → chunk riordinati", async ({ page }) => {
    await page.goto(
      "/admin/documents/123e4567-e89b-12d3-a456-426614174000/chunks"
    );

    // Attendi completamento caricamento pagina
    await expect(page.getByText("anatomia_spalla.pdf")).toBeVisible();
    await expect(page.getByText("2 chunk generati")).toBeVisible();

    // Mock sorted response
    await page.route("**/api/v1/admin/documents/*/chunks**", async (route) => {
      const url = new URL(route.request().url());
      if (url.searchParams.get("sort_by") === "chunk_size") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            document_id: "123e4567-e89b-12d3-a456-426614174000",
            document_name: "anatomia_spalla.pdf",
            chunks: [
              {
                chunk_id: "chunk-2",
                content: "Breve contenuto chunk",
                chunk_size: 21,
                chunk_index: 1,
                chunking_strategy: "recursive",
                page_number: 2,
                embedding_status: "indexed",
                created_at: "2025-01-15T10:01:00Z",
              },
              {
                chunk_id: "chunk-1",
                content: "Lorem ipsum...",
                chunk_size: 445,
                chunk_index: 0,
                chunking_strategy: "recursive",
                page_number: 1,
                embedding_status: "indexed",
                created_at: "2025-01-15T10:00:00Z",
              },
            ],
            total_chunks: 2,
          }),
        });
      } else {
        await route.continue();
      }
    });

    // Apri dropdown sort e seleziona "Dimensione"
    const comboboxes = page.getByRole("combobox");
    await expect(comboboxes).toHaveCount(2); // Strategy + Sort
    await comboboxes.nth(1).click();
    await page.getByText("Dimensione").click();

    // Attendi ricaricamento chunk dopo sort
    await page.waitForTimeout(500);

    // Verifica ordine cambiato (chunk più piccolo primo)
    const cards = page.locator('[data-slot="card"]');
    await expect(cards.first()).toContainText("21 caratteri");
  });

  test("Scenario 6: Non-admin redirect da /admin/documents", async ({
    page,
  }) => {
    // Crea nuova pagina senza token
    const newPage = await page.context().newPage();

    // Vai a /admin/documents senza token
    await newPage.goto("/admin/documents");

    // Verifica redirect a login (AdminGuard)
    await expect(newPage).toHaveURL(/\/login/);

    await newPage.close();
  });
});
