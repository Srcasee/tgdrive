import { defineConfig, loadEnv } from "vite";
import path from "path";
import { resolve } from "path";
import { include } from "./build/optimize";
import postcssPresetEnv from "postcss-preset-env";
import { createVitePlugins } from "./build/vite-plugin";

// tgdrive serves the complete SnowAdmin console under /admin.
export default defineConfig(({ mode }) => {
  const root = process.cwd();
  const env: any = loadEnv(mode, root);
  return {
    base: env.VITE_PUBLIC_PATH || "/admin/",
    server: {
      open: true,
      proxy: {
        "/api": {
          target: env.VITE_APP_BASE_URL,
          changeOrigin: true,
          rewrite: p => p.replace(/^\/api/, "")
        },
        "/auth": {
          target: env.VITE_APP_BASE_URL,
          changeOrigin: true
        }
      }
    },
    plugins: createVitePlugins(env),
    resolve: {
      alias: {
        "@assets": path.join(__dirname, "src/assets"),
        "@": resolve(__dirname, "./src")
      }
    },
    css: {
      postcss: { plugins: [postcssPresetEnv()] },
      preprocessorOptions: { scss: { additionalData: `@use "@/style/var/index.scss" as *; ` } }
    },
    optimizeDeps: { include },
    build: {
      outDir: "dist",
      minify: "terser",
      terserOptions: {
        compress: { keep_infinity: true, drop_console: true, drop_debugger: true },
        format: { comments: false }
      },
      assetsInlineLimit: 50 * 1024,
      chunkSizeWarningLimit: 50000,
      rollupOptions: {
        output: {
          chunkFileNames: "static/js/[name]-[hash].js",
          entryFileNames: "static/js/[name]-[hash].js",
          assetFileNames: "static/[ext]/[name]-[hash].[ext]"
        }
      }
    }
  };
});
