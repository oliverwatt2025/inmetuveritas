import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/miner-status.json": {
        target: "http://100.108.50.71:8081",
        changeOrigin: true,
      },
    },
  },
});