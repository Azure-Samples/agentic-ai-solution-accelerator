import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Minimal Vite config. Partners typically only need to tweak `server.proxy`
// during local dev (if they don't want to set CORS on the FastAPI side) and
// the build target.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
