from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import json
import os
import base64
import time
import hmac
from http import cookies

from auth import (
    verify_username,
    verify_password,
    create_session,
    get_session,
    delete_session,
)
import supabase_client

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8765"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def make_session_cookie(handler, session_id):
    cookie = (
        f"br_session={session_id}; "
        "HttpOnly; Path=/; SameSite=Strict"
    )

    if is_https(handler):
        cookie += "; Secure"

    return cookie


def get_request_session(handler):
    raw_cookie = handler.headers.get("Cookie", "")
    if not raw_cookie:
        return None, None

    parsed = cookies.SimpleCookie()

    try:
        parsed.load(raw_cookie)
    except cookies.CookieError:
        return None, None

    morsel = parsed.get("br_session")
    if not morsel:
        return None, None

    session_id = morsel.value
    session = get_session(session_id)

    if not session:
        return None, None

    return session_id, session


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

            username = str(data.get("username", ""))
            password = str(data.get("password", ""))

            if not username or not password:
                record_login_failure(ip)
                self.send_json(
                    {"error": "Kullanici adi ve sifre gerekli."},
                    400
                )
                return

            if not verify_username(username):
                record_login_failure(ip)
                self.send_json(
                    {"error": "Kullanici adi veya sifre hatali."},
                    401
                )
                return

            if not verify_password(password):
                record_login_failure(ip)
                self.send_json(
                    {"error": "Kullanici adi veya sifre hatali."},
                    401
                )
                return

            clear_login_failures(ip)

            session_id, csrf_token = create_session()

            cookie_value = (
                f"br_session={session_id}; "
                "HttpOnly; Path=/; SameSite=Strict"
            )

            if is_https(self):
                cookie_value += "; Secure"

            body = json.dumps(
                {
                    "success": True,
                    "csrfToken": csrf_token
                },
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
            session_id, session = get_request_session(self)

            if not session:
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

        super().do_GET()

    def handle_logout(self):
        session_id, session = get_request_session(self)

        if session_id:
            delete_session(session_id)

        self.send_response(200)
        self.send_header(
            "Set-Cookie",
            "br_session=; HttpOnly; Path=/; Max-Age=0; SameSite=Strict"
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

        session_id, session = get_request_session(self)

        if not session:
            self.send_json(
                {"error": "Yetkisiz erişim."},
                401
            )
            return

        csrf_token = self.headers.get("X-CSRF-Token", "")

        if not csrf_token or not hmac.compare_digest(
            csrf_token,
            session["csrf"]
        ):
            self.send_json(
                {"error": "Geçersiz CSRF token."},
                403
            )
            return

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
                        content_type
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
            })

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
