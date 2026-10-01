import { defineConfig } from "vite";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

function burakApiPlugin() {
  return {
    name: "burak-review-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, `http://${req.headers.host}`);

        if (url.pathname === "/api/products" && req.method === "GET") {
          try {
            const data = readFileSync(
              join(__dirname, "frontend", "data", "products.json"),
              "utf-8"
            );
            const products = JSON.parse(data);
            res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
            res.end(JSON.stringify(products));
          } catch (err) {
            res.writeHead(500, { "Content-Type": "application/json; charset=utf-8" });
            res.end(JSON.stringify({ error: "Ürünler alınamadı." }));
          }
          return;
        }

        if (url.pathname === "/api/auth/me" && req.method === "GET") {
          res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ authenticated: true }));
          return;
        }

        if (url.pathname === "/api/auth/login" && req.method === "POST") {
          res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ success: true, csrfToken: "preview-csrf-token" }));
          return;
        }

        if (url.pathname === "/api/auth/logout" && req.method === "POST") {
          res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ success: true }));
          return;
        }

        if (url.pathname === "/api/products" && req.method === "POST") {
          res.writeHead(201, { "Content-Type": "application/json; charset=utf-8" });
          res.end(JSON.stringify({ success: true, id: 999, message: "Ürün kaydedildi (önizleme)." }));
          return;
        }

        next();
      });
    },
  };
}

export default defineConfig({
  root: "frontend",
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: "dist",
  },
  plugins: [burakApiPlugin()],
});
