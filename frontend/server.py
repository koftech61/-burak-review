from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, quote
import json
import os
import re
import base64
import time
import hmac
import hashlib
import urllib.error
import urllib.parse
import urllib.request
from http import cookies

import supabase_client

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8765"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SITE_URL = os.environ.get(
    "SITE_URL",
    "https://burak-review.onrender.com"
).rstrip("/")

SESSION_COOKIE = "br_admin"
SESSION_DURATION = 60 * 60 * 4

LOGIN_FAILURES = {}
MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW = 600


def get_client_ip(handler):
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def is_https(handler):
    return (
        handler.headers.get("X-Forwarded-Proto", "").lower() == "https"
        or os.environ.get("RENDER") == "true"
    )


def make_session_cookie(handler, value, max_age=None):
    cookie = (
        f"{SESSION_COOKIE}={value}; "
        "HttpOnly; Path=/; SameSite=Strict"
    )

    if max_age is not None:
        cookie += f"; Max-Age={max_age}"

    if is_https(handler):
        cookie += "; Secure"

    return cookie


def get_request_session(handler):
    raw_cookie = handler.headers.get("Cookie", "")
    if not raw_cookie:
        return None

    parsed = cookies.SimpleCookie()

    try:
        parsed.load(raw_cookie)
    except cookies.CookieError:
        return None

    morsel = parsed.get(SESSION_COOKIE)
    if not morsel:
        return None

    return verify_session_value(morsel.value)


def sign_session_value(payload_b64):
    _, key = supabase_client.get_config()
    return hmac.new(
        key.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def build_session_value(access_token, refresh_token):
    payload = json.dumps({
        "access": access_token,
        "refresh": refresh_token,
        "issued": time.time()
    })
    payload_b64 = base64.urlsafe_b64encode(
        payload.encode("utf-8")
    ).decode("ascii")

    signature = sign_session_value(payload_b64)

    return f"{payload_b64}.{signature}"


def verify_session_value(value):
    if not value or "." not in value:
        return None

    payload_b64, signature = value.rsplit(".", 1)
    expected = sign_session_value(payload_b64)

    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(
            base64.urlsafe_b64decode(
                payload_b64.encode("ascii")
            ).decode("utf-8")
        )
    except (ValueError, json.JSONDecodeError):
        return None

    if time.time() - payload.get("issued", 0) > SESSION_DURATION:
        return None

    return payload


def supabase_auth_request(path, body):
    url, key = supabase_client.get_config()

    if not url or not key:
        raise RuntimeError("Supabase ayarlari eksik.")

    request = urllib.request.Request(
        f"{url}/auth/v1/{path}",
        data=json.dumps(body).encode("utf-8"),
        method="POST"
    )
    request.add_header("apikey", key)
    request.add_header("Content-Type", "application/json")

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def refresh_session(session):
    try:
        return supabase_auth_request(
            "token?grant_type=refresh_token",
            {"refresh_token": session.get("refresh", "")}
        )
    except Exception:
        return None


def login_allowed(ip):
    now = time.time()
    entry = LOGIN_FAILURES.get(ip)

    if not entry or now - entry["first"] > LOGIN_WINDOW:
        LOGIN_FAILURES[ip] = {
            "count": 0,
            "first": now
        }
        return True

    return entry["count"] < MAX_LOGIN_FAILURES


def record_login_failure(ip):
    now = time.time()
    entry = LOGIN_FAILURES.get(ip)

    if not entry or now - entry["first"] > LOGIN_WINDOW:
        LOGIN_FAILURES[ip] = {
            "count": 1,
            "first": now
        }
    else:
        entry["count"] += 1


def clear_login_failures(ip):
    LOGIN_FAILURES.pop(ip, None)


def authenticate(handler):
    session = get_request_session(handler)

    if not session:
        return None

    access_token = session.get("access", "")

    try:
        user = supabase_client.get_user(access_token)
    except Exception:
        refreshed = refresh_session(session)

        if not refreshed or not refreshed.get("access_token"):
            return None

        access_token = refreshed["access_token"]

        handler.send_header(
            "Set-Cookie",
            make_session_cookie(
                handler,
                build_session_value(
                    access_token,
                    refreshed.get("refresh_token", "")
                ),
                max_age=SESSION_DURATION
            )
        )

        try:
            user = supabase_client.get_user(access_token)
        except Exception:
            return None

    user_id = user.get("id")

    if not user_id:
        return None

    try:
        if not supabase_client.is_admin(access_token, user_id):
            return None
    except Exception:
        return None

    return {
        "access_token": access_token,
        "user_id": user_id
    }


class BurakReviewServer(SimpleHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()
        self.wfile.write(body)

    def handle_login(self):
        ip = get_client_ip(self)

        if not login_allowed(ip):
            self.send_response(429)
            self.send_header("Retry-After", "600")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            body = b'{"error":"Cok fazla basarisiz giris denemesi. Daha sonra tekrar deneyin."}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if content_length <= 0 or content_length > 16 * 1024:
                self.send_json(
                    {"error": "Gecersiz istek."},
                    400
                )
                return

            raw_data = self.rfile.read(content_length)
            data = json.loads(raw_data.decode("utf-8"))

            email = str(data.get("email", "")).strip()
            password = str(data.get("password", ""))

            if not email or not password:
                record_login_failure(ip)
                self.send_json(
                    {"error": "E-posta ve sifre gerekli."},
                    400
                )
                return

            try:
                auth = supabase_auth_request(
                    "token?grant_type=password",
                    {"email": email, "password": password}
                )
            except urllib.error.HTTPError:
                record_login_failure(ip)
                self.send_json(
                    {"error": "E-posta veya sifre hatali."},
                    401
                )
                return
            except Exception:
                record_login_failure(ip)
                self.send_json(
                    {"error": "Giris sirasinda sunucu hatasi olustu."},
                    500
                )
                return

            access_token = auth.get("access_token", "")
            refresh_token = auth.get("refresh_token", "")
            user_id = (auth.get("user") or {}).get("id")

            if not access_token or not user_id:
                record_login_failure(ip)
                self.send_json(
                    {"error": "E-posta veya sifre hatali."},
                    401
                )
                return

            try:
                admin = supabase_client.is_admin(access_token, user_id)
            except Exception:
                admin = False

            if not admin:
                record_login_failure(ip)
                self.send_json(
                    {"error": "Bu hesabin yonetici yetkisi yok."},
                    403
                )
                return

            clear_login_failures(ip)

            cookie_value = make_session_cookie(
                self,
                build_session_value(access_token, refresh_token),
                max_age=SESSION_DURATION
            )

            body = json.dumps(
                {"success": True},
                ensure_ascii=False
            ).encode("utf-8")

            self.send_response(200)
            self.send_header("Set-Cookie", cookie_value)
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8"
            )
            self.send_header(
                "Content-Length",
                str(len(body))
            )
            self.end_headers()
            self.wfile.write(body)

        except (ValueError, json.JSONDecodeError):
            self.send_json(
                {"error": "Gecersiz istek."},
                400
            )
        except Exception:
            print("LOGIN ERROR")
            self.send_json(
                {"error": "Giris sirasinda sunucu hatasi olustu."},
                500
            )

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/auth/me":
            admin = authenticate(self)

            if not admin:
                self.send_json(
                    {"authenticated": False},
                    401
                )
                return

            self.send_json(
                {"authenticated": True},
                200
            )
            return

        if path == "/api/products":
            try:
                products = supabase_client.list_products()

                self.send_json(products)

            except Exception as error:
                print("GET ERROR:", error)

                self.send_json(
                    {"error": "Ürünler alınamadı."},
                    500
                )

            return

        if path == "/robots.txt":
            self.send_text(self.build_robots())
            return

        if path == "/sitemap.xml":
            self.send_xml(self.build_sitemap())
            return

        if path in ("/product.html", "/urun"):
            query = parse_qs(urlparse(self.path).query)
            slug = (query.get("urun") or [""])[0].strip()

            if slug:
                self.send_product_page(slug)
                return

        super().do_GET()

    def send_text(self, text):
        body = text.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_xml(self, text):
        body = text.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def build_robots(self):
        return (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin.html\n"
            "Disallow: /admin-login.html\n"
            "Disallow: /api/\n"
            f"\nSitemap: {SITE_URL}/sitemap.xml\n"
        )

    def build_sitemap(self):
        try:
            products = supabase_client.list_products()
        except Exception as error:
            print("SITEMAP ERROR:", error)
            products = []

        entries = [
            (f"{SITE_URL}/", "1.0", "daily")
        ]

        for product in products:
            slug = quote(str(product.get("slug", "")), safe="")

            if not slug:
                continue

            entries.append((
                f"{SITE_URL}/product.html?urun={slug}",
                "0.8",
                "weekly"
            ))

        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        ]

        for loc, priority, frequency in entries:
            lines.append(
                "  <url>"
                f"<loc>{loc}</loc>"
                f"<changefreq>{frequency}</changefreq>"
                f"<priority>{priority}</priority>"
                "</url>"
            )

        lines.append("</urlset>")

        return "\n".join(lines)

    def send_product_page(self, slug):
        path = os.path.join(BASE_DIR, "product.html")

        try:
            with open(path, "r", encoding="utf-8") as page_file:
                html = page_file.read()
        except OSError:
            self.send_error(404)
            return

        try:
            products = supabase_client.list_products()
        except Exception as error:
            print("PRERENDER ERROR:", error)
            products = []

        product = next(
            (
                item
                for item in products
                if str(item.get("slug", "")).strip() == slug
            ),
            None
        )

        if product:
            html = self.render_product_seo(html, product, slug)

        body = html.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def render_product_seo(self, html, product, slug):
        name = product.get("name", "")
        brand = product.get("brand", "")
        description = (
            product.get("description")
            or f"{name} teknik özellikleri, artıları, eksileri ve Burak Review değerlendirmesi."
        )
        description = re.sub(r"\s+", " ", str(description)).strip()[:160]

        title = f"{name} İncelemesi | Burak Review"
        canonical = (
            f"{SITE_URL}/product.html?urun={quote(str(slug), safe='')}"
        )

        image = product.get("image") or f"{SITE_URL}/og-image.jpg"

        if not str(image).lower().startswith("http"):
            image = f"{SITE_URL}/{str(image).lstrip('/')}"

        specs = (
            product.get("specs")
            if isinstance(product.get("specs"), dict)
            else {}
        )

        structured = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": name,
            "description": product.get("description") or "",
            "category": product.get("category") or "",
            "url": canonical,
            "brand": {"@type": "Brand", "name": brand},
            "image": [image],
            "additionalProperty": [
                {
                    "@type": "PropertyValue",
                    "name": key,
                    "value": str(value)
                }
                for key, value in specs.items()
            ]
        }

        try:
            rating = float(product.get("rating") or 0)
        except (TypeError, ValueError):
            rating = 0

        if rating > 0:
            structured["review"] = {
                "@type": "Review",
                "reviewRating": {
                    "@type": "Rating",
                    "ratingValue": rating,
                    "bestRating": 5,
                    "worstRating": 0
                },
                "author": {
                    "@type": "Organization",
                    "name": "Burak Review"
                },
                "reviewBody": (
                    product.get("finalVerdict")
                    or product.get("verdict")
                    or ""
                )
            }

        def replace(pattern, replacement, source):
            return re.sub(
                pattern,
                lambda match: replacement,
                source,
                count=1
            )

        html = replace(
            r"<title>.*?</title>",
            f"<title>{title}</title>",
            html
        )

        html = replace(
            r'<meta\s+name="description"\s+content="[^"]*"\s*/?>',
            f'<meta name="description" content="{self.escape(description)}">',
            html
        )

        html = replace(
            r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>',
            f'<link rel="canonical" href="{self.escape(canonical)}">',
            html
        )

        html = replace(
            r'<meta\s+property="og:title"\s+content="[^"]*"\s*/?>',
            f'<meta property="og:title" content="{self.escape(title)}">',
            html
        )

        html = replace(
            r'<meta\s+property="og:description"\s+content="[^"]*"\s*/?>',
            f'<meta property="og:description" content="{self.escape(description)}">',
            html
        )

        html = replace(
            r'<meta\s+property="og:url"\s+content="[^"]*"\s*/?>',
            f'<meta property="og:url" content="{self.escape(canonical)}">',
            html
        )

        html = replace(
            r'<meta\s+property="og:image"\s+content="[^"]*"\s*/?>',
            f'<meta property="og:image" content="{self.escape(image)}">',
            html
        )

        html = replace(
            r'<meta\s+name="twitter:title"\s+content="[^"]*"\s*/?>',
            f'<meta name="twitter:title" content="{self.escape(title)}">',
            html
        )

        html = replace(
            r'<meta\s+name="twitter:description"\s+content="[^"]*"\s*/?>',
            f'<meta name="twitter:description" content="{self.escape(description)}">',
            html
        )

        html = replace(
            r'<meta\s+name="twitter:image"\s+content="[^"]*"\s*/?>',
            f'<meta name="twitter:image" content="{self.escape(image)}">',
            html
        )

        script = (
            '<script type="application/ld+json">'
            + json.dumps(structured, ensure_ascii=False)
            + "</script>"
        )

        html = html.replace("</head>", f"    {script}\n</head>", 1)

        return html

    @staticmethod
    def escape(value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def handle_logout(self):
        self.send_response(200)
        self.send_header(
            "Set-Cookie",
            make_session_cookie(self, "", max_age=0)
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        body = b'{"success":true}'
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/auth/login":
            self.handle_login()
            return

        if path == "/api/auth/logout":
            self.handle_logout()
            return

        if path != "/api/products":
            self.send_json(
                {"error": "Geçersiz API adresi."},
                404
            )
            return

        admin = authenticate(self)

        if not admin:
            self.send_json(
                {"error": "Yetkisiz erişim."},
                401
            )
            return

        token = admin["access_token"]

        try:
            content_length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            if content_length <= 0:
                self.send_json(
                    {"error": "Veri gönderilmedi."},
                    400
                )
                return

            raw_data = self.rfile.read(
                content_length
            )

            data = json.loads(
                raw_data.decode("utf-8")
            )

            required = [
                "slug",
                "brand",
                "name",
                "category",
                "rating"
            ]

            for field in required:
                if not data.get(field):
                    self.send_json(
                        {
                            "error":
                            f"Eksik alan: {field}"
                        },
                        400
                    )
                    return

            rating = float(data["rating"])

            if rating < 0 or rating > 5:
                self.send_json(
                    {
                        "error":
                        "Puan 0 ile 5 arasında olmalı."
                    },
                    400
                )
                return

            # Fotoğraf yükleme
            image_path = data.get("image", "")
            image_data = data.get("imageData")

            if image_data:
                try:
                    if not isinstance(image_data, str):
                        raise ValueError("Geçersiz fotoğraf verisi.")

                    if "," not in image_data:
                        raise ValueError("Geçersiz fotoğraf formatı.")

                    header, encoded = image_data.split(",", 1)

                    mime_map = {
                        "data:image/jpeg;base64": (".jpg", "image/jpeg"),
                        "data:image/png;base64": (".png", "image/png"),
                        "data:image/webp;base64": (".webp", "image/webp")
                    }

                    mime_entry = mime_map.get(header.lower())

                    if not mime_entry:
                        raise ValueError(
                            "Sadece JPG, PNG veya WebP yüklenebilir."
                        )

                    extension, content_type = mime_entry

                    raw_image = base64.b64decode(
                        encoded,
                        validate=True
                    )

                    if len(raw_image) > 5 * 1024 * 1024:
                        raise ValueError(
                            "Fotoğraf 5 MB'dan büyük olamaz."
                        )

                    image_path = supabase_client.upload_image(
                        data["slug"],
                        raw_image,
                        extension,
                        content_type,
                        token=token
                    )

                except Exception as image_error:
                    self.send_json(
                        {
                            "error":
                            str(image_error)
                        },
                        400
                    )
                    return

            saved = supabase_client.insert_product({
                "slug": data["slug"],
                "brand": data["brand"],
                "name": data["name"],
                "category": data["category"],
                "image": image_path,
                "rating": rating,
                "verdict": data.get("verdict", ""),
                "price": data.get("price", ""),
                "description": data.get("description", ""),
                "pros": data.get("pros", []),
                "cons": data.get("cons", []),
                "shouldBuy": data.get("shouldBuy", []),
                "shouldNotBuy": data.get("shouldNotBuy", []),
                "specs": data.get("specs", {}),
                "finalVerdict": data.get("finalVerdict", "")
            }, token=token)

            self.send_json(
                {
                    "success": True,
                    "message":
                    "Ürün başarıyla kaydedildi.",
                    "id": saved["id"]
                },
                201
            )

        except json.JSONDecodeError:
            self.send_json(
                {
                    "error":
                    "Geçersiz JSON verisi."
                },
                400
            )

        except Exception as error:
            print("POST ERROR:", error)

            self.send_json(
                {
                    "error":
                    "Sunucu hatası oluştu."
                },
                500
            )

    def do_DELETE(self):
        path = urlparse(self.path).path

        if path != "/api/products":
            self.send_json(
                {"error": "Geçersiz API adresi."},
                404
            )
            return

        admin = authenticate(self)

        if not admin:
            self.send_json(
                {"error": "Yetkisiz erişim."},
                401
            )
            return

        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            if content_length <= 0:
                self.send_json(
                    {"error": "Veri gönderilmedi."},
                    400
                )
                return

            raw_data = self.rfile.read(content_length)
            data = json.loads(raw_data.decode("utf-8"))

            product_id = str(data.get("id", "")).strip()

            if not product_id:
                self.send_json(
                    {"error": "Ürün kimliği gerekli."},
                    400
                )
                return

            supabase_client.delete_product(
                product_id,
                admin["access_token"]
            )

            self.send_json(
                {
                    "success": True,
                    "message": "Ürün silindi."
                },
                200
            )

        except json.JSONDecodeError:
            self.send_json(
                {"error": "Geçersiz JSON verisi."},
                400
            )

        except Exception as error:
            print("DELETE ERROR:", error)

            self.send_json(
                {"error": "Sunucu hatası oluştu."},
                500
            )


os.chdir(BASE_DIR)

server = ThreadingHTTPServer(
    (HOST, PORT),
    BurakReviewServer
)

print("🔥 BURAK REVIEW BACKEND HAZIR")
print("🌐 http://127.0.0.1:8765")
print("📦 API: /api/products")
print("⛔ CTRL+C = durdur")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n🛑 SERVER DURDURULDU")
finally:
    server.server_close()
