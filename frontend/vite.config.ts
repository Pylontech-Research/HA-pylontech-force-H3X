import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

function injectPanelCss(): Plugin {
  return {
    name: "fh3x-inline-panel-css",
    generateBundle(_options, bundle) {
      const css = Object.values(bundle)
        .filter((item): item is { type: "asset"; fileName: string; source: string | Uint8Array } => item.type === "asset" && item.fileName.endsWith(".css"))
        .map((item) => String(item.source))
        .join("\n");
      const entry = bundle["fh3x-panel.js"];
      if (entry && entry.type === "chunk" && css) {
        entry.code = `(()=>{const s=document.createElement("style");s.dataset.fh3x="panel";s.textContent=${JSON.stringify(css)};document.head.appendChild(s)})();\n${entry.code}`;
      }
      for (const [fileName, item] of Object.entries(bundle)) {
        if (item.type === "asset" && fileName.endsWith(".css")) delete bundle[fileName];
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), injectPanelCss()],
  build: {
    outDir: "../custom_components/pylontech_fh3x/frontend",
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      input: "index.html",
      output: {
        entryFileNames: "fh3x-panel.js",
        chunkFileNames: "chunks/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});
