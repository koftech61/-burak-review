import { defineConfig } from "vite";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

function readEnv() {
  const env = {};
  try {
    const raw = readFileSync(join(__dirname, ".env"), "utf-8");
    for (const line of raw.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
      const index = trimmed.indexOf("=");
      env[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
    }
  } catch {
    // .env yoksa ortam degiskenlerine dusulur
  }
  return env;
}

const fileEnv = readEnv();
const SUPABASE_URL =
  process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || fileEnv.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY =
  process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || fileEnv.VITE_SUPABASE_ANON_KEY;

function supabaseHeaders() {
  return {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    "Content-Type": "application/json",
  };
}

function rowToProduct(row) {
  return {
    id: row.id,
    slug: row.slug,
    brand: row.brand,
    name: row.name,
    category: row.category,
    image: row.image || "",
    rating: Number(row.rating),
    verdict: row.verdict || "",
    price: row.price || "",
    description: row.description || "",
    pros: row.pros || [],
    cons: row.cons || [],
    shouldBuy: row.should_buy || [],
    shouldNotBuy: row.should_not_buy || [],
    specs: row.specs || {},
    finalVerdict: row.final_verdict || "",
  };
}

function sendJson(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf-8");
}

function burakApiPlugin() {
  return {
    name: "burak-review-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, `http://${req.headers.host}`);

        if (url.pathname === "/api/products" && req.method === "GET") {
          try {
            const response = await fetch(
              `${SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc`,
              { headers: supabaseHeaders() }
            );

            if (!response.ok) {
              throw new Error(`Supabase ${response.status}`);
            }

            const rows = await response.json();
            sendJson(res, 200, rows.map(rowToProduct));
          } catch (err) {
            sendJson(res, 500, { error: "Ürünler alınamadı." });
          }
          return;
        }

        if (url.pathname === "/api/auth/me" && req.method === "GET") {
          sendJson(res, 200, { authenticated: true });
          return;
        }

        if (url.pathname === "/api/auth/login" && req.method === "POST") {
          sendJson(res, 200, { success: true, csrfToken: "preview-csrf-token" });
          return;
        }

        if (url.pathname === "/api/auth/logout" && req.method === "POST") {
          sendJson(res, 200, { success: true });
          return;
        }

        if (url.pathname === "/api/products" && req.method === "POST") {
          try {
            const data = JSON.parse(await readBody(req));

            const response = await fetch(`${SUPABASE_URL}/rest/v1/products`, {
              method: "POST",
              headers: { ...supabaseHeaders(), Prefer: "return=representation" },
              body: JSON.stringify({
                slug: data.slug,
                brand: data.brand,
                name: data.name,
                category: data.category,
                image: data.image || "",
                rating: Number(data.rating),
                verdict: data.verdict || "",
                price: data.price || "",
                description: data.description || "",
                pros: data.pros || [],
                cons: data.cons || [],
                should_buy: data.shouldBuy || [],
                should_not_buy: data.shouldNotBuy || [],
                specs: data.specs || {},
                final_verdict: data.finalVerdict || "",
              }),
            });

            if (!response.ok) {
              throw new Error(`Supabase ${response.status}`);
            }

            const rows = await response.json();
            sendJson(res, 201, {
              success: true,
              message: "Ürün başarıyla kaydedildi.",
              id: rows[0]?.id,
            });
          } catch (err) {
            sendJson(res, 500, { error: "Ürün kaydedilemedi." });
          }
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
