import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { defineConfig } from "vite";

const manifest = JSON.parse(
  readFileSync(
    resolve(__dirname, "../custom_components/high_school_sports_scores/manifest.json"),
    "utf8",
  ),
) as { version: string };

export default defineConfig({
  define: {
    __HSSS_CARD_VERSION__: JSON.stringify(manifest.version),
  },
  build: {
    outDir: resolve(__dirname, "../custom_components/high_school_sports_scores/www"),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/high-school-sports-scores-card.ts"),
      formats: ["iife", "es"],
      fileName: (format) =>
        format === "iife"
          ? "high-school-sports-scores-card.js"
          : "high-school-sports-scores-card.module.js",
      name: "HighSchoolSportsScoresCard",
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
