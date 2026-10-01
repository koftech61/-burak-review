import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def _load_env_file():
    values = {}

    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

    return values


_FILE_ENV = _load_env_file()


def get_config():
    url = (
        os.environ.get("SUPABASE_URL")
        or os.environ.get("VITE_SUPABASE_URL")
        or _FILE_ENV.get("VITE_SUPABASE_URL", "")
    )

    key = (
        os.environ.get("SUPABASE_ANON_KEY")
        or os.environ.get("VITE_SUPABASE_ANON_KEY")
        or _FILE_ENV.get("VITE_SUPABASE_ANON_KEY", "")
    )

    return url.rstrip("/"), key


def is_configured():
    url, key = get_config()
    return bool(url and key)


def _request(method, path, body=None, headers=None, params=None, timeout=30):
    url, key = get_config()

    if not url or not key:
        raise RuntimeError("Supabase ayarlari eksik.")

    full_url = f"{url}{path}"

    if params:
        full_url += "?" + urllib.parse.urlencode(params)

    data = None

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    request = urllib.request.Request(full_url, data=data, method=method)
    request.add_header("apikey", key)
    request.add_header("Authorization", f"Bearer {key}")

    if data is not None:
        request.add_header("Content-Type", "application/json")

    for name, value in (headers or {}).items():
        request.add_header(name, value)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()

            if not raw:
                return None

            return json.loads(raw.decode("utf-8"))

    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Supabase hatasi ({error.code}): {detail}"
        ) from error


def row_to_product(row):
    return {
        "id": row["id"],
        "slug": row["slug"],
        "brand": row["brand"],
        "name": row["name"],
        "category": row["category"],
        "image": row.get("image") or "",
        "rating": float(row["rating"]),
        "verdict": row.get("verdict") or "",
        "price": row.get("price") or "",
        "description": row.get("description") or "",
        "pros": row.get("pros") or [],
        "cons": row.get("cons") or [],
        "shouldBuy": row.get("should_buy") or [],
        "shouldNotBuy": row.get("should_not_buy") or [],
        "specs": row.get("specs") or {},
        "finalVerdict": row.get("final_verdict") or ""
    }


def list_products():
    rows = _request(
        "GET",
        "/rest/v1/products",
        params={
            "select": "*",
            "order": "created_at.desc"
        }
    )

    return [
        row_to_product(row)
        for row in (rows or [])
    ]


def insert_product(payload):
    body = {
        "slug": payload["slug"],
        "brand": payload["brand"],
        "name": payload["name"],
        "category": payload["category"],
        "image": payload.get("image", ""),
        "rating": float(payload["rating"]),
        "verdict": payload.get("verdict", ""),
        "price": payload.get("price", ""),
        "description": payload.get("description", ""),
        "pros": payload.get("pros", []),
        "cons": payload.get("cons", []),
        "should_buy": payload.get("shouldBuy", []),
        "should_not_buy": payload.get("shouldNotBuy", []),
        "specs": payload.get("specs", {}),
        "final_verdict": payload.get("finalVerdict", "")
    }

    rows = _request(
        "POST",
        "/rest/v1/products",
        body=body,
        headers={
            "Prefer": "return=representation"
        }
    )

    if not rows:
        raise RuntimeError("Urun kaydedilemedi.")

    return row_to_product(rows[0])


def upload_image(slug, raw_bytes, extension, content_type):
    url, key = get_config()

    if not url or not key:
        raise RuntimeError("Supabase ayarlari eksik.")

    filename = (
        f"{slug}-{uuid.uuid4().hex[:8]}{extension}"
    )

    object_path = f"product-images/{filename}"
    upload_url = f"{url}/storage/v1/object/{object_path}"

    request = urllib.request.Request(
        upload_url,
        data=raw_bytes,
        method="POST"
    )
    request.add_header("apikey", key)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("Content-Type", content_type)
    request.add_header("x-upsert", "true")

    try:
        with urllib.request.urlopen(
            request,
            timeout=60
        ) as response:
            response.read()

    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"Fotoğraf yüklenemedi ({error.code}): {detail}"
        ) from error

    return f"{url}/storage/v1/object/public/{object_path}"
