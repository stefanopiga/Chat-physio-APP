/* eslint-disable @typescript-eslint/no-explicit-any */
import { test, expect } from "@playwright/test";

test.describe("Story 4.1.5: Admin Dashboard Hub", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const mockSession = {
        user: {
          id: "mock-admin-id",
          email: "admin@test.com",
          app_metadata: { role: "admin" },
        },
      };

      (window as any).__mockAuthService = {
        getSession: async () => ({
          data: { session: mockSession },
          error: null,
        }),
        onAuthStateChange: (callback: any) => {
          setTimeout(() => callback("SIGNED_IN", mockSession), 0);
          return { data: { subscription: { unsubscribe: () => {} } } };
        },
        isAdmin: () => true,
        isStudent: () => false,
        isAuthenticated: () => true,
      };

      sessionStorage.setItem("temp_jwt", "mock-admin-token");
    });
  });

  test("E2E-001: Admin sees Debug RAG card on dashboard", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(
      page.locator("h1:has-text('Dashboard Amministratore')")
    ).toBeVisible();
    await expect(page.locator("text=Debug RAG")).toBeVisible();
  });

  test("E2E-002: Clicking Debug RAG card navigates to /admin/debug", async ({
    page,
  }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    await page.click("text=Debug RAG");
    await expect(page).toHaveURL("/admin/debug");
  });

  test("E2E-003: Analytics card navigable (no Coming Soon)", async ({
    page,
  }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Analytics Dashboard")).toBeVisible();
    // Card attiva: nessun badge "Coming Soon"
    await expect(page.locator("text=Coming Soon")).toHaveCount(0);
  });

  test("E2E-004: Analytics card click navigates to /admin/analytics", async ({
    page,
  }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    await page.click("text=Analytics Dashboard");
    await expect(page).toHaveURL("/admin/analytics");
  });

  test("E2E-005: Non-admin redirect (student login) → /", async ({ page }) => {
    await page.addInitScript(() => {
      const mockStudentSession = {
        user: {
          id: "mock-student-id",
          email: "student@test.com",
          app_metadata: { role: "student" },
        },
      };

      (window as any).__mockAuthService = {
        getSession: async () => ({
          data: { session: mockStudentSession },
          error: null,
        }),
        onAuthStateChange: (callback: any) => {
          setTimeout(() => callback("SIGNED_IN", mockStudentSession), 0);
          return { data: { subscription: { unsubscribe: () => {} } } };
        },
        isAdmin: () => false,
        isStudent: () => true,
        isAuthenticated: () => true,
      };
    });

    await page.goto("/admin/dashboard");
    await page.waitForTimeout(1000);

    await expect(page).toHaveURL("/login");
  });

  test("E2E-006: Email display shows real admin email", async ({ page }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    await expect(page.locator("text=Benvenuto, admin@test.com")).toBeVisible();
  });

  test("E2E-007: Responsive mobile - 1 column layout", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    const grid = page
      .locator(".grid.grid-cols-1.gap-4.md\\:grid-cols-2")
      .first();
    await expect(grid).toBeVisible();
    expect(await grid.getAttribute("class")).toContain("grid-cols-1");
  });

  test("E2E-008: Responsive desktop - 2 column layout", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");

    const grid = page
      .locator(".grid.grid-cols-1.gap-4.md\\:grid-cols-2")
      .first();
    await expect(grid).toBeVisible();
    const classes = await grid.getAttribute("class");
    expect(classes).toContain("grid-cols-1");
    expect(classes).toContain("md:grid-cols-2");
  });
});
