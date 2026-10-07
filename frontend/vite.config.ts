import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  base: "/admin/",
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/auth": "http://127.0.0.1:8080",
      "/catalog": "http://127.0.0.1:8080",
      "/resources": "http://127.0.0.1:8080",
    },
  },
  build: {
    outDir: "dist",
  },
});
