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

const SESSION_COOKIE = "br_admin";
const SESSION_DURATION = 60 * 60 * 4;

function supabaseHeaders(token) {
  return {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${token || SUPABASE_ANON_KEY}`,
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

function sendJson(res, status, payload, extraHeaders) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    ...(extraHeaders || {}),
  });
  res.end(JSON.stringify(payload));
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf-8");
}

function parseCookies(req) {
  const header = req.headers.cookie || "";
  const jar = {};
  for (const part of header.split(";")) {
    const index = part.indexOf("=");
    if (index === -1) continue;
    jar[part.slice(0, index).trim()] = part.slice(index + 1).trim();
  }
  return jar;
}

function readSession(req) {
  const raw = parseCookies(req)[SESSION_COOKIE];
  if (!raw) return null;
  try {
    const parsed = JSON.parse(Buffer.from(raw, "base64").toString("utf-8"));
    if (Date.now() / 1000 - parsed.issued > SESSION_DURATION) return null;
    return parsed;
  } catch {
    return null;
  }
}

function sessionCookie(session, maxAge) {
  const value = session
    ? Buffer.from(JSON.stringify(session)).toString("base64")
    : "";
  return `${SESSION_COOKIE}=${value}; HttpOnly; Path=/; SameSite=Strict; Max-Age=${maxAge}`;
}

async function supabaseUser(accessToken) {
  const response = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: supabaseHeaders(accessToken),
  });
  if (!response.ok) return null;
  return response.json();
}

async function isAdmin(accessToken, userId) {
  const response = await fetch(
    `${SUPABASE_URL}/rest/v1/admins?select=user_id&user_id=eq.${encodeURIComponent(userId)}`,
    { headers: supabaseHeaders(accessToken) }
  );
  if (!response.ok) return false;
  const rows = await response.json();
  return Array.isArray(rows) && rows.length > 0;
}

async function verifyAdmin(req) {
  const session = readSession(req);
  if (!session || !session.access) return null;

  let user = await supabaseUser(session.access);

  if (!user && session.refresh) {
    const refreshed = await fetch(
      `${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`,
      {
        method: "POST",
        headers: supabaseHeaders(),
        body: JSON.stringify({ refresh_token: session.refresh }),
      }
    );

    if (refreshed.ok) {
      const data = await refreshed.json();
      user = await supabaseUser(data.access_token);
      if (user) session.access = data.access_token;
    }
  }

  if (!user || !user.id) return null;
  if (!(await isAdmin(session.access, user.id))) return null;

  return { token: session.access, session };
}

function burakApiPlugin() {
  return {
    name: "burak-review-api",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = new URL(req.url, `http://${req.headers.host}`);

        if (url.pathname === "/api/auth/login" && req.method === "POST") {
          try {
            const data = JSON.parse(await readBody(req));
            const auth = await fetch(
              `${SUPABASE_URL}/auth/v1/token?grant_type=password`,
              {
                method: "POST",
                headers: supabaseHeaders(),
                body: JSON.stringify({
                  email: String(data.email || ""),
                  password: String(data.password || ""),
                }),
              }
            );

            if (!auth.ok) {
              sendJson(res, 401, { error: "E-posta veya şifre hatalı." });
              return;
            }

            const session = await auth.json();
            const admin = await isAdmin(
              session.access_token,
              session.user?.id
            );

            if (!admin) {
              sendJson(res, 403, { error: "Bu hesabın yönetici yetkisi yok." });
              return;
            }

            const issued = Math.floor(Date.now() / 1000);
            const cookie = sessionCookie(
              {
                access: session.access_token,
                refresh: session.refresh_token,
                issued,
              },
              SESSION_DURATION
            );

            sendJson(res, 200, { success: true }, { "Set-Cookie": cookie });
          } catch {
            sendJson(res, 500, { error: "Giriş sırasında hata oluştu." });
          }
          return;
        }

        if (url.pathname === "/api/auth/me" && req.method === "GET") {
          const admin = await verifyAdmin(req);
          if (!admin) {
            sendJson(res, 401, { authenticated: false });
            return;
          }
          sendJson(res, 200, { authenticated: true });
          return;
        }

        if (url.pathname === "/api/auth/logout" && req.method === "POST") {
          sendJson(res, 200, { success: true }, { "Set-Cookie": sessionCookie(null, 0) });
          return;
        }

        if (url.pathname === "/api/products" && req.method === "GET") {
          try {
            const response = await fetch(
              `${SUPABASE_URL}/rest/v1/products?select=*&order=created_at.desc`,
              { headers: supabaseHeaders() }
            );

            if (!response.ok) throw new Error(`Supabase ${response.status}`);

            const rows = await response.json();
            sendJson(res, 200, rows.map(rowToProduct));
          } catch {
            sendJson(res, 500, { error: "Ürünler alınamadı." });
          }
          return;
        }

        if (url.pathname === "/api/products" && req.method === "POST") {
          const admin = await verifyAdmin(req);

          if (!admin) {
            sendJson(res, 401, { error: "Yetkisiz erişim." });
            return;
          }

          try {
            const data = JSON.parse(await readBody(req));

            const response = await fetch(`${SUPABASE_URL}/rest/v1/products`, {
              method: "POST",
              headers: { ...supabaseHeaders(admin.token), Prefer: "return=representation" },
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

            if (!response.ok) throw new Error(`Supabase ${response.status}`);

            const rows = await response.json();
            sendJson(res, 201, {
              success: true,
              message: "Ürün başarıyla kaydedildi.",
              id: rows[0]?.id,
            });
          } catch {
            sendJson(res, 500, { error: "Ürün kaydedilemedi." });
          }
          return;
        }

        if (url.pathname === "/api/products" && req.method === "DELETE") {
          const admin = await verifyAdmin(req);

          if (!admin) {
            sendJson(res, 401, { error: "Yetkisiz erişim." });
            return;
          }

          try {
            const data = JSON.parse(await readBody(req));
            const id = String(data.id || "").trim();

            if (!id) {
              sendJson(res, 400, { error: "Ürün kimliği gerekli." });
              return;
            }

            const response = await fetch(
              `${SUPABASE_URL}/rest/v1/products?id=eq.${encodeURIComponent(id)}`,
              {
                method: "DELETE",
                headers: { ...supabaseHeaders(admin.token), Prefer: "return=minimal" },
              }
            );

            if (!response.ok) throw new Error(`Supabase ${response.status}`);

            sendJson(res, 200, { success: true, message: "Ürün silindi." });
          } catch {
            sendJson(res, 500, { error: "Ürün silinemedi." });
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
