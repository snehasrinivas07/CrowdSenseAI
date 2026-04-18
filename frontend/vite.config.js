import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API requests to backend during local development
    // so you don't need to set VITE_API_URL locally
    proxy: {
      "/crowd":  "http://localhost:8000",
      "/events": "http://localhost:8000",
      "/nudges": "http://localhost:8000",
      "/chat":   "http://localhost:8000",
      "/admin":  "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ws":     {
        target:    "ws://localhost:8000",
        ws:        true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
