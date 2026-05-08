import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./tests/unit/setup.ts"],
      include: ["tests/unit/**/*.{test,spec}.{ts,tsx}"],
      coverage: {
        reporter: ["text", "html"],
        include: ["src/**/*.{ts,tsx}"],
        exclude: ["src/**/*.d.ts", "src/main.tsx", "src/lib/api-types.ts"],
      },
    },
  }),
);
