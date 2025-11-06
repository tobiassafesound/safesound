import { defineConfig } from "astro/config";
import tailwind from "@astrojs/tailwind";
import node from "@astrojs/node";

export default defineConfig({
  output: "server",
  adapter: node({
    mode: "standalone", // Render ejecuta como Node app única
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
    port: Number(process.env.PORT) || 4321, // ✅ aseguras tipo numérico
  },
});
