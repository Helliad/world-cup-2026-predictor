import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the static bundle works both locally and under a GitHub
// Pages project subpath (e.g. /worldcup-2026-predictor/) without rebuilding.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: false },
});
