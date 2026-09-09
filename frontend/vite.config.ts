import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    outDir: resolve(__dirname, "../custom_components/maxpreps/www"),
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/maxpreps-card.ts"),
      formats: ["es"],
      fileName: () => "maxpreps-card.js",
    },
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
  test: {
    environment: "node",
    include: ["tests/**/*.test.ts"],
  },
});
