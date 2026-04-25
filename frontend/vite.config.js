import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@":           path.resolve(__dirname, "src"),
      "@components": path.resolve(__dirname, "src/components"),
      "@pages":      path.resolve(__dirname, "src/pages"),
      "@hooks":      path.resolve(__dirname, "src/hooks"),
      "@api":        path.resolve(__dirname, "src/api"),
      "@types":      path.resolve(__dirname, "src/types"),
      "@lib":        path.resolve(__dirname, "src/lib"),
      "@context":    path.resolve(__dirname, "src/context"),
    },
  },
});
