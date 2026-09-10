import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: resolve(__dirname, "../custom_components/high_school_sports_scores/www"),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/high-school-sports-scores-card.ts"),
      formats: ["es"],
      fileName: () => "high-school-sports-scores-card.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  test: {
    environment: "happy-dom",
    include: ["tests/**/*.test.ts"],
  },
});
