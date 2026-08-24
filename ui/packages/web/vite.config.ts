import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
    port: 4002,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/dsh/": {
        target: process.env.DSH_DEV_PROXY_TARGET || "http://localhost:8080",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
