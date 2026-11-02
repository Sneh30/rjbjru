import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    // Playwright specs use a different runner and must not be collected by
    // Vitest. The default include pattern would otherwise pick up e2e/*.spec.ts.
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    testTimeout: 20_000,
    hookTimeout: 20_000,
    css: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/**/*.d.ts", "src/test/**"],
      thresholds: {
        lines: 55,
        functions: 50,
        statements: 55,
        branches: 45,
      },
    },
  },
});
