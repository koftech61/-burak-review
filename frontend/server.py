from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
import sqlite3
import json
import os
import base64
import uuid
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

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8765"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "products.db")
PRODUCTS_JSON = os.path.join(BASE_DIR, "data", "products.json")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    db = sqlite3.connect(DB_PATH)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            brand TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT,
            rating REAL NOT NULL,
            verdict TEXT,
            price TEXT,
            description TEXT,
            pros TEXT,
            cons TEXT,
            should_buy TEXT,
            should_not_buy TEXT,
            specs TEXT,
            final_verdict TEXT
        )
        """
    )

    if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        if os.path.exists(PRODUCTS_JSON):
            with open(PRODUCTS_JSON, "r", encoding="utf-8") as f:
                products = json.load(f)

            for data in products:
                db.execute(
                    """
                    INSERT INTO products (
                        slug, brand, name, category, image,
                        rating, verdict, price, description,
                        pros, cons, should_buy, should_not_buy,
                        specs, final_verdict
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["slug"],
                        data["brand"],
                        data["name"],
                        data["category"],
                        data.get("image", ""),
                        data["rating"],
                        data.get("verdict", ""),
                        data.get("price", ""),
                        data.get("description", ""),
                        json.dumps(data.get("pros", []), ensure_ascii=False),
                        json.dumps(data.get("cons", []), ensure_ascii=False),
                        json.dumps(data.get("shouldBuy", []), ensure_ascii=False),
                        json.dumps(data.get("shouldNotBuy", []), ensure_ascii=False),
                        json.dumps(data.get("specs", {}), ensure_ascii=False),
                        data.get("finalVerdict", "")
                    )
                )

    db.commit()
    db.close()


def row_to_product(row):
    return {
        "id": row["id"],
        "slug": row["slug"],
        "brand": row["brand"],
        "name": row["name"],
        "category": row["category"],
        "image": row["image"],
        "rating": row["rating"],
        "verdict": row["verdict"],
        "price": row["price"],
        "description": row["description"],
        "pros": json.loads(row["pros"] or "[]"),
        "cons": json.loads(row["cons"] or "[]"),
        "shouldBuy": json.loads(row["should_buy"] or "[]"),
        "shouldNotBuy": json.loads(row["should_not_buy"] or "[]"),
        "specs": json.loads(row["specs"] or "{}"),
        "finalVerdict": row["final_verdict"]
    }


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
                db = get_db()

                rows = db.execute(
                    "SELECT * FROM products ORDER BY id DESC"
                ).fetchall()

                db.close()

                products = [
                    row_to_product(row)
                    for row in rows
                ]

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
                        "data:image/jpeg;base64": ".jpg",
                        "data:image/png;base64": ".png",
                        "data:image/webp;base64": ".webp"
                    }

                    extension = mime_map.get(header.lower())

                    if not extension:
                        raise ValueError(
                            "Sadece JPG, PNG veya WebP yüklenebilir."
                        )

                    raw_image = base64.b64decode(
                        encoded,
                        validate=True
                    )

                    if len(raw_image) > 5 * 1024 * 1024:
                        raise ValueError(
                            "Fotoğraf 5 MB'dan büyük olamaz."
                        )

                    filename = (
                        f"{data['slug']}-"
                        f"{uuid.uuid4().hex[:8]}"
                        f"{extension}"
                    )

                    filepath = os.path.join(
                        IMAGES_DIR,
                        filename
                    )

                    with open(filepath, "wb") as image_file:
                        image_file.write(raw_image)

                    image_path = f"images/{filename}"

                except Exception as image_error:
                    self.send_json(
                        {
                            "error":
                            str(image_error)
                        },
                        400
                    )
                    return

            db = get_db()

            db.execute(
                """
                INSERT INTO products (
                    slug,
                    brand,
                    name,
                    category,
                    image,
                    rating,
                    verdict,
                    price,
                    description,
                    pros,
                    cons,
                    should_buy,
                    should_not_buy,
                    specs,
                    final_verdict
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["slug"],
                    data["brand"],
                    data["name"],
                    data["category"],
                    image_path,
                    rating,
                    data.get("verdict", ""),
                    data.get("price", ""),
                    data.get("description", ""),
                    json.dumps(
                        data.get("pros", []),
                        ensure_ascii=False
                    ),
                    json.dumps(
                        data.get("cons", []),
                        ensure_ascii=False
                    ),
                    json.dumps(
                        data.get("shouldBuy", []),
                        ensure_ascii=False
                    ),
                    json.dumps(
                        data.get("shouldNotBuy", []),
                        ensure_ascii=False
                    ),
                    json.dumps(
                        data.get("specs", {}),
                        ensure_ascii=False
                    ),
                    data.get(
                        "finalVerdict",
                        ""
                    )
                )
            )

            db.commit()

            product_id = db.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            db.close()

            self.send_json(
                {
                    "success": True,
                    "message":
                    "Ürün başarıyla kaydedildi.",
                    "id": product_id
                },
                201
            )

        except sqlite3.IntegrityError:
            self.send_json(
                {
                    "error":
                    "Bu ürün zaten mevcut."
                },
                409
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


init_db()
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
