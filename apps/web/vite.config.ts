import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: [
      "tests/**",
      "playwright.config.ts",
      "playwright-report/**",
      "test-results/**",
    ],
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
  },
});
