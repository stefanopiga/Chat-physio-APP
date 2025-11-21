// vite.config.ts
import { defineConfig } from "file:///C:/Users/user/Desktop/Claude-Code/fisio-rag-master/APPLICAZIONE/node_modules/.pnpm/vitest@2.1.9_@types+node@24_9e8844aabc0d19092db4bfdbb5c7065b/node_modules/vitest/dist/config.js";
import react from "file:///C:/Users/user/Desktop/Claude-Code/fisio-rag-master/APPLICAZIONE/node_modules/.pnpm/@vitejs+plugin-react@4.7.0__66dd7fa274ca549e892340d291b18683/node_modules/@vitejs/plugin-react/dist/index.js";
import tailwindcss from "file:///C:/Users/user/Desktop/Claude-Code/fisio-rag-master/APPLICAZIONE/node_modules/.pnpm/@tailwindcss+vite@4.1.13_vi_a2cdefd2a48c220be145466f5eb30e97/node_modules/@tailwindcss/vite/dist/index.mjs";
import path from "path";
var __vite_injected_original_dirname = "C:\\Users\\user\\Desktop\\Claude-Code\\fisio-rag-master\\APPLICAZIONE\\apps\\web";
var vite_config_default = defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src")
    }
  },
  build: {
    // Ottimizzazioni per production
    target: "esnext",
    minify: "terser",
    terserOptions: {
      compress: {
        drop_console: true,
        // Rimuovi console.log in production
        drop_debugger: true,
        pure_funcs: ["console.log", "console.info", "console.debug"]
      }
    },
    // Code splitting strategy
    rollupOptions: {
      output: {
        manualChunks: {
          // Separa vendor chunks per migliore caching
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "ui-vendor": [
            "@radix-ui/react-dialog",
            "@radix-ui/react-label",
            "@radix-ui/react-select",
            "@radix-ui/react-slot"
          ],
          // Charts separato - usato solo in AnalyticsPage
          "charts": ["recharts"],
          "supabase": ["@supabase/supabase-js"]
        }
      }
    },
    // Chunk size warnings
    chunkSizeWarningLimit: 1e3,
    // Source maps per debugging (disabilita in production se non necessari)
    sourcemap: false
  },
  // Ottimizzazioni per dev
  server: {
    hmr: {
      overlay: true
    }
  },
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
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxVc2Vyc1xcXFx1c2VyXFxcXERlc2t0b3BcXFxcQ2xhdWRlLUNvZGVcXFxcZmlzaW8tcmFnLW1hc3RlclxcXFxBUFBMSUNBWklPTkVcXFxcYXBwc1xcXFx3ZWJcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkM6XFxcXFVzZXJzXFxcXHVzZXJcXFxcRGVza3RvcFxcXFxDbGF1ZGUtQ29kZVxcXFxmaXNpby1yYWctbWFzdGVyXFxcXEFQUExJQ0FaSU9ORVxcXFxhcHBzXFxcXHdlYlxcXFx2aXRlLmNvbmZpZy50c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vQzovVXNlcnMvdXNlci9EZXNrdG9wL0NsYXVkZS1Db2RlL2Zpc2lvLXJhZy1tYXN0ZXIvQVBQTElDQVpJT05FL2FwcHMvd2ViL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVzdC9jb25maWdcIjtcclxuaW1wb3J0IHJlYWN0IGZyb20gXCJAdml0ZWpzL3BsdWdpbi1yZWFjdFwiO1xyXG5pbXBvcnQgdGFpbHdpbmRjc3MgZnJvbSBcIkB0YWlsd2luZGNzcy92aXRlXCI7XHJcbmltcG9ydCBwYXRoIGZyb20gXCJwYXRoXCI7XHJcblxyXG4vLyBodHRwczovL3ZpdGUuZGV2L2NvbmZpZy9cclxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcclxuICBwbHVnaW5zOiBbcmVhY3QoKSwgdGFpbHdpbmRjc3MoKV0sXHJcbiAgcmVzb2x2ZToge1xyXG4gICAgYWxpYXM6IHtcclxuICAgICAgXCJAXCI6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsIFwiLi9zcmNcIiksXHJcbiAgICB9LFxyXG4gIH0sXHJcbiAgYnVpbGQ6IHtcclxuICAgIC8vIE90dGltaXp6YXppb25pIHBlciBwcm9kdWN0aW9uXHJcbiAgICB0YXJnZXQ6IFwiZXNuZXh0XCIsXHJcbiAgICBtaW5pZnk6IFwidGVyc2VyXCIsXHJcbiAgICB0ZXJzZXJPcHRpb25zOiB7XHJcbiAgICAgIGNvbXByZXNzOiB7XHJcbiAgICAgICAgZHJvcF9jb25zb2xlOiB0cnVlLCAvLyBSaW11b3ZpIGNvbnNvbGUubG9nIGluIHByb2R1Y3Rpb25cclxuICAgICAgICBkcm9wX2RlYnVnZ2VyOiB0cnVlLFxyXG4gICAgICAgIHB1cmVfZnVuY3M6IFtcImNvbnNvbGUubG9nXCIsIFwiY29uc29sZS5pbmZvXCIsIFwiY29uc29sZS5kZWJ1Z1wiXSxcclxuICAgICAgfSxcclxuICAgIH0sXHJcbiAgICAvLyBDb2RlIHNwbGl0dGluZyBzdHJhdGVneVxyXG4gICAgcm9sbHVwT3B0aW9uczoge1xyXG4gICAgICBvdXRwdXQ6IHtcclxuICAgICAgICBtYW51YWxDaHVua3M6IHtcclxuICAgICAgICAgIC8vIFNlcGFyYSB2ZW5kb3IgY2h1bmtzIHBlciBtaWdsaW9yZSBjYWNoaW5nXHJcbiAgICAgICAgICBcInJlYWN0LXZlbmRvclwiOiBbXCJyZWFjdFwiLCBcInJlYWN0LWRvbVwiLCBcInJlYWN0LXJvdXRlci1kb21cIl0sXHJcbiAgICAgICAgICBcInVpLXZlbmRvclwiOiBbXHJcbiAgICAgICAgICAgIFwiQHJhZGl4LXVpL3JlYWN0LWRpYWxvZ1wiLFxyXG4gICAgICAgICAgICBcIkByYWRpeC11aS9yZWFjdC1sYWJlbFwiLFxyXG4gICAgICAgICAgICBcIkByYWRpeC11aS9yZWFjdC1zZWxlY3RcIixcclxuICAgICAgICAgICAgXCJAcmFkaXgtdWkvcmVhY3Qtc2xvdFwiLFxyXG4gICAgICAgICAgXSxcclxuICAgICAgICAgIC8vIENoYXJ0cyBzZXBhcmF0byAtIHVzYXRvIHNvbG8gaW4gQW5hbHl0aWNzUGFnZVxyXG4gICAgICAgICAgXCJjaGFydHNcIjogW1wicmVjaGFydHNcIl0sXHJcbiAgICAgICAgICBcInN1cGFiYXNlXCI6IFtcIkBzdXBhYmFzZS9zdXBhYmFzZS1qc1wiXSxcclxuICAgICAgICB9LFxyXG4gICAgICB9LFxyXG4gICAgfSxcclxuICAgIC8vIENodW5rIHNpemUgd2FybmluZ3NcclxuICAgIGNodW5rU2l6ZVdhcm5pbmdMaW1pdDogMTAwMCxcclxuICAgIC8vIFNvdXJjZSBtYXBzIHBlciBkZWJ1Z2dpbmcgKGRpc2FiaWxpdGEgaW4gcHJvZHVjdGlvbiBzZSBub24gbmVjZXNzYXJpKVxyXG4gICAgc291cmNlbWFwOiBmYWxzZSxcclxuICB9LFxyXG4gIC8vIE90dGltaXp6YXppb25pIHBlciBkZXZcclxuICBzZXJ2ZXI6IHtcclxuICAgIGhtcjoge1xyXG4gICAgICBvdmVybGF5OiB0cnVlLFxyXG4gICAgfSxcclxuICB9LFxyXG4gIHRlc3Q6IHtcclxuICAgIGluY2x1ZGU6IFtcInNyYy8qKi8qLnRlc3QudHNcIiwgXCJzcmMvKiovKi50ZXN0LnRzeFwiXSxcclxuICAgIGV4Y2x1ZGU6IFtcclxuICAgICAgXCJ0ZXN0cy8qKlwiLFxyXG4gICAgICBcInBsYXl3cmlnaHQuY29uZmlnLnRzXCIsXHJcbiAgICAgIFwicGxheXdyaWdodC1yZXBvcnQvKipcIixcclxuICAgICAgXCJ0ZXN0LXJlc3VsdHMvKipcIixcclxuICAgIF0sXHJcbiAgICBlbnZpcm9ubWVudDogXCJqc2RvbVwiLFxyXG4gICAgc2V0dXBGaWxlczogW1wiLi92aXRlc3Quc2V0dXAudHNcIl0sXHJcbiAgfSxcclxufSk7XHJcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBNFosU0FBUyxvQkFBb0I7QUFDemIsT0FBTyxXQUFXO0FBQ2xCLE9BQU8saUJBQWlCO0FBQ3hCLE9BQU8sVUFBVTtBQUhqQixJQUFNLG1DQUFtQztBQU16QyxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsTUFBTSxHQUFHLFlBQVksQ0FBQztBQUFBLEVBQ2hDLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLE9BQU87QUFBQSxJQUN0QztBQUFBLEVBQ0Y7QUFBQSxFQUNBLE9BQU87QUFBQTtBQUFBLElBRUwsUUFBUTtBQUFBLElBQ1IsUUFBUTtBQUFBLElBQ1IsZUFBZTtBQUFBLE1BQ2IsVUFBVTtBQUFBLFFBQ1IsY0FBYztBQUFBO0FBQUEsUUFDZCxlQUFlO0FBQUEsUUFDZixZQUFZLENBQUMsZUFBZSxnQkFBZ0IsZUFBZTtBQUFBLE1BQzdEO0FBQUEsSUFDRjtBQUFBO0FBQUEsSUFFQSxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixjQUFjO0FBQUE7QUFBQSxVQUVaLGdCQUFnQixDQUFDLFNBQVMsYUFBYSxrQkFBa0I7QUFBQSxVQUN6RCxhQUFhO0FBQUEsWUFDWDtBQUFBLFlBQ0E7QUFBQSxZQUNBO0FBQUEsWUFDQTtBQUFBLFVBQ0Y7QUFBQTtBQUFBLFVBRUEsVUFBVSxDQUFDLFVBQVU7QUFBQSxVQUNyQixZQUFZLENBQUMsdUJBQXVCO0FBQUEsUUFDdEM7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBO0FBQUEsSUFFQSx1QkFBdUI7QUFBQTtBQUFBLElBRXZCLFdBQVc7QUFBQSxFQUNiO0FBQUE7QUFBQSxFQUVBLFFBQVE7QUFBQSxJQUNOLEtBQUs7QUFBQSxNQUNILFNBQVM7QUFBQSxJQUNYO0FBQUEsRUFDRjtBQUFBLEVBQ0EsTUFBTTtBQUFBLElBQ0osU0FBUyxDQUFDLG9CQUFvQixtQkFBbUI7QUFBQSxJQUNqRCxTQUFTO0FBQUEsTUFDUDtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsTUFDQTtBQUFBLElBQ0Y7QUFBQSxJQUNBLGFBQWE7QUFBQSxJQUNiLFlBQVksQ0FBQyxtQkFBbUI7QUFBQSxFQUNsQztBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
