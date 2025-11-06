import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import node from "@astrojs/node";

export default defineConfig({
  output: "server",
  adapter: node({
    mode: "standalone",
  }),
  integrations: [tailwind()],
  vite: {
    resolve: {
      alias: {
        "@": new URL("./src/", import.meta.url).pathname,
      },
    },
  },
  server: {
    host: true, // ✅ obliga a escuchar en 0.0.0.0 (no solo localhost)
    port: Number(process.env.PORT) || 4321, // ✅ puerto correcto
  },
});
