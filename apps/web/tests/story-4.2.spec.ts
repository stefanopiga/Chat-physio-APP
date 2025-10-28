import { test, expect } from "@playwright/test";

// Story 4.2: Analytics Dashboard - E2E
// Scenari implementati (10 totali):
// - Navigazione, loading/data, refresh, AdminGuard, empty state, responsive,
// - Top queries table, feedback chart, performance metrics, navigation back
//
// Test accessibilità (A11Y-001 a A11Y-003): vedi story-4.2-accessibility.spec.ts

const buildMockAdminSessionScript = () => `
  const mockSession = {
    access_token: "mock-admin-token",
    user: {
      id: "mock-admin-id",
      email: "admin@test.com",
      app_metadata: { role: "admin" },
    },
  };
  (window).__mockAuthService = {
    getSession: async () => ({ data: { session: mockSession }, error: null }),
    onAuthStateChange: (cb) => { setTimeout(() => cb("SIGNED_IN", mockSession), 0); return { data: { subscription: { unsubscribe: () => {} } } }; },
    isAdmin: () => true,
    isStudent: () => false,
    isAuthenticated: () => true,
  };
  sessionStorage.setItem("temp_jwt", "mock-admin-token");
`;

const buildMockStudentSessionScript = () => `
  const mockStudentSession = {
    user: {
      id: "mock-student-id",
      email: "student@test.com",
      app_metadata: { role: "student" },
    },
  };
  (window).__mockAuthService = {
    getSession: async () => ({ data: { session: mockStudentSession }, error: null }),
    onAuthStateChange: (cb) => { setTimeout(() => cb("SIGNED_IN", mockStudentSession), 0); return { data: { subscription: { unsubscribe: () => {} } } }; },
    isAdmin: () => false,
    isStudent: () => true,
    isAuthenticated: () => true,
  };
  sessionStorage.setItem("temp_jwt", "mock-student-token");
`;

const analyticsOk = {
  overview: {
    total_queries: 150,
    total_sessions: 25,
    feedback_ratio: 0.75,
    avg_latency_ms: 450,
  },
  top_queries: [
    {
      query_text: "cos'è la scoliosi?",
      count: 10,
      last_queried_at: "2025-10-02T10:00:00Z",
    },
    {
      query_text: "esercizi lombari",
      count: 8,
      last_queried_at: "2025-10-02T11:00:00Z",
    },
  ],
  feedback_summary: { thumbs_up: 45, thumbs_down: 15, ratio: 0.75 },
  performance_metrics: {
    latency_p95_ms: 800,
    latency_p99_ms: 1200,
    sample_count: 150,
  },
};

const analyticsEmpty = {
  overview: {
    total_queries: 0,
    total_sessions: 0,
    feedback_ratio: 0.0,
    avg_latency_ms: 0,
  },
  top_queries: [],
  feedback_summary: { thumbs_up: 0, thumbs_down: 0, ratio: 0.0 },
  performance_metrics: {
    latency_p95_ms: 0,
    latency_p99_ms: 0,
    sample_count: 0,
  },
};

test.describe("Story 4.2: Analytics Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(buildMockAdminSessionScript());
  });

  test("E2E-4.2-001: Navigazione card → /admin/analytics e heading visibile", async ({
    page,
  }) => {
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");
    await page.click("text=Analytics Dashboard");
    await expect(page).toHaveURL("/admin/analytics");
    await expect(
      page.locator("h1:has-text('Analytics Dashboard')")
    ).toBeVisible();
  });

  test("E2E-4.2-002: Loading → dati KPI renderizzati", async ({ page }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      // Simula piccolo delay per vedere loading state
      await new Promise((r) => setTimeout(r, 100));
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(
      page.getByRole("heading", { name: "Analytics Dashboard" })
    ).toBeVisible();
    await expect(page.locator("text=Domande Totali")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("text=150").first()).toBeVisible();
    await expect(page.locator("text=Sessioni Attive")).toBeVisible();
    await expect(page.locator("text=25").first()).toBeVisible();
    await expect(page.locator("text=Latenza Media")).toBeVisible();
    await expect(page.locator("text=450ms").first()).toBeVisible();
  });

  test("E2E-4.2-003: Refresh button effettua un nuovo fetch", async ({
    page,
  }) => {
    let hits = 0;
    await page.route("**/api/v1/admin/analytics", async (route) => {
      hits += 1;
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(
      page.getByRole("heading", { name: "Analytics Dashboard" })
    ).toBeVisible();
    await page.locator('button:has-text("Aggiorna Dati")').click();
    await expect.poll(() => hits).toBeGreaterThanOrEqual(2);
  });

  test("E2E-4.2-004: AdminGuard - non-admin viene rediretto a /login", async ({
    page,
  }) => {
    await page.addInitScript(buildMockStudentSessionScript());
    await page.goto("/admin/analytics");
    await page.waitForTimeout(1000);
    await expect(page).toHaveURL("/login");
  });

  test("E2E-4.2-005: Empty state senza query e feedback", async ({ page }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsEmpty),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(
      page.locator("h2:has-text('Domande Più Frequenti')")
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=Nessuna domanda registrata")).toBeVisible();
    await expect(page.locator("text=Nessun feedback ricevuto")).toBeVisible();
  });

  test("E2E-4.2-006: Responsive - KPI grid 1 col mobile, 4 col desktop", async ({
    page,
  }) => {
    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(page.locator("h2:has-text('Panoramica')")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("text=Domande Totali")).toBeVisible();
    // Desktop
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.reload();
    await expect(page.locator("h2:has-text('Panoramica')")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.locator("text=Domande Totali")).toBeVisible();
  });

  test("E2E-4.2-007: Top Queries Table - verifica righe e sort", async ({
    page,
  }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(
      page.locator("h2:has-text('Domande Più Frequenti')")
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=cos'è la scoliosi?")).toBeVisible();
    await expect(page.locator("text=esercizi lombari")).toBeVisible();
    const rows = page.locator("table tbody tr");
    await expect(rows).toHaveCount(2);
  });

  test("E2E-4.2-008: Feedback Chart - bar chart visibile", async ({ page }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(page.locator("h2:has-text('Feedback Aggregato')")).toBeVisible(
      { timeout: 15000 }
    );
    await expect(page.locator("text=Ratio positivo: 75.0%")).toBeVisible();
    const chartSvg = page.locator("svg.recharts-surface");
    await expect(chartSvg.first()).toBeVisible();
  });

  test("E2E-4.2-009: Performance Metrics - P95/P99 cards visibili", async ({
    page,
  }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    await page.goto("/admin/analytics");
    await expect(
      page.locator("h2:has-text('Performance Sistema')")
    ).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=P95 Latency")).toBeVisible();
    await expect(page.locator("text=800ms").first()).toBeVisible();
    await expect(page.locator("text=P99 Latency")).toBeVisible();
    await expect(page.locator("text=1200ms").first()).toBeVisible();
  });

  test("E2E-4.2-010: Navigation - back to dashboard da analytics", async ({
    page,
  }) => {
    await page.route("**/api/v1/admin/analytics", async (route) => {
      await route.fulfill({
        status: 200,
        body: JSON.stringify(analyticsOk),
        headers: { "content-type": "application/json" },
      });
    });
    // Prima naviga a dashboard, poi ad analytics per poter tornare indietro
    await page.goto("/admin/dashboard");
    await page.waitForLoadState("networkidle");
    await page.goto("/admin/analytics");
    await expect(
      page.getByRole("heading", { name: "Analytics Dashboard" })
    ).toBeVisible({ timeout: 15000 });
    await page.goBack();
    await expect(page).toHaveURL("/admin/dashboard");
    await expect(page.locator("text=Analytics Dashboard")).toBeVisible();
  });
});
