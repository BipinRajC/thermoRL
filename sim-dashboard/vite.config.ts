import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import { TanStackRouterVite } from "@tanstack/router-vite-plugin";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = {...process.env, ...loadEnv(mode, process.cwd())};

  return {
    base: env.VITE_BASE_PATH,
    plugins: [react(), TanStackRouterVite()],
    server: {
      port: Number(env.VITE_PORT ?? 9080),
    },
}});
