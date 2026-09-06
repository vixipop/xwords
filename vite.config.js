import { defineConfig } from "vite";

// Plain HTML/CSS/JS app. Files in public/ (data/, assets/) are served at the
// site root as-is and copied verbatim into dist/ on build.
export default defineConfig({
  base: "/",
  server: { port: 5173, open: true },
  build: { outDir: "dist", emptyOutDir: true },
});
