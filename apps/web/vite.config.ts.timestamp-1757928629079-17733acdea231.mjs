// vite.config.ts
import { defineConfig } from "file:///C:/Users/user/Desktop/Claude-Code/fisio-rag-master/APPLICAZIONE/node_modules/.pnpm/vitest@2.1.9_@types+node@24.3.1_jsdom@25.0.1/node_modules/vitest/dist/config.js";
import react from "file:///C:/Users/user/Desktop/Claude-Code/fisio-rag-master/APPLICAZIONE/node_modules/.pnpm/@vitejs+plugin-react@5.0.2_vite@7.1.5_@types+node@24.3.1_/node_modules/@vitejs/plugin-react/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [react()],
  test: {
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: [
      "tests/**",
      "playwright.config.ts",
      "playwright-report/**",
      "test-results/**"
    ],
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"]
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxVc2Vyc1xcXFx1c2VyXFxcXERlc2t0b3BcXFxcQ2xhdWRlLUNvZGVcXFxcZmlzaW8tcmFnLW1hc3RlclxcXFxBUFBMSUNBWklPTkVcXFxcYXBwc1xcXFx3ZWJcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkM6XFxcXFVzZXJzXFxcXHVzZXJcXFxcRGVza3RvcFxcXFxDbGF1ZGUtQ29kZVxcXFxmaXNpby1yYWctbWFzdGVyXFxcXEFQUExJQ0FaSU9ORVxcXFxhcHBzXFxcXHdlYlxcXFx2aXRlLmNvbmZpZy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vQzovVXNlcnMvdXNlci9EZXNrdG9wL0NsYXVkZS1Db2RlL2Zpc2lvLXJhZy1tYXN0ZXIvQVBQTElDQVpJT05FL2FwcHMvd2ViL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVzdC9jb25maWdcIjtcbmltcG9ydCByZWFjdCBmcm9tIFwiQHZpdGVqcy9wbHVnaW4tcmVhY3RcIjtcblxuLy8gaHR0cHM6Ly92aXRlLmRldi9jb25maWcvXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbcmVhY3QoKV0sXG4gIHRlc3Q6IHtcbiAgICBpbmNsdWRlOiBbXCJzcmMvKiovKi50ZXN0LnRzXCIsIFwic3JjLyoqLyoudGVzdC50c3hcIl0sXG4gICAgZXhjbHVkZTogW1xuICAgICAgXCJ0ZXN0cy8qKlwiLFxuICAgICAgXCJwbGF5d3JpZ2h0LmNvbmZpZy50c1wiLFxuICAgICAgXCJwbGF5d3JpZ2h0LXJlcG9ydC8qKlwiLFxuICAgICAgXCJ0ZXN0LXJlc3VsdHMvKipcIixcbiAgICBdLFxuICAgIGVudmlyb25tZW50OiBcImpzZG9tXCIsXG4gICAgc2V0dXBGaWxlczogW1wiLi92aXRlc3Quc2V0dXAudHNcIl0sXG4gIH0sXG59KTtcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBNFosU0FBUyxvQkFBb0I7QUFDemIsT0FBTyxXQUFXO0FBR2xCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLENBQUM7QUFBQSxFQUNqQixNQUFNO0FBQUEsSUFDSixTQUFTLENBQUMsb0JBQW9CLG1CQUFtQjtBQUFBLElBQ2pELFNBQVM7QUFBQSxNQUNQO0FBQUEsTUFDQTtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsSUFDRjtBQUFBLElBQ0EsYUFBYTtBQUFBLElBQ2IsWUFBWSxDQUFDLG1CQUFtQjtBQUFBLEVBQ2xDO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
