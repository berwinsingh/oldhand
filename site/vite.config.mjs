import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  build: {
    outDir: "dist/client",
  },
  optimizeDeps: {
    include: ["react", "react-dom/client"],
  },
  server: {
    host: "0.0.0.0",
    allowedHosts: ["terminal.local"],
    // The page imports the skill, the example report and the plugin manifest
    // from the repository root at build time, so the dev server must serve
    // those folders (and only those: the dev server binds all interfaces).
    fs: { allow: [".", "../skills", "../examples", "../.claude-plugin", "../bench"] },
    warmup: {
      clientFiles: ["./src/main.jsx"],
    },
  },
  plugins: [react()],
});
