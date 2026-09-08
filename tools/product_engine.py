import json
import re
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = BASE_DIR / "frontend" / "data" / "products.json"
RESEARCH_DIR = BASE_DIR / "tools" / "research"


BRANDS = {
    "iphone": "Apple",
    "airpods": "Apple",
    "macbook": "Apple",
    "ipad": "Apple",
    "galaxy": "Samsung",
    "pixel": "Google",
    "sony": "Sony",
    "wh-": "Sony",
    "jbl": "JBL",
    "tune": "JBL",
    "logitech": "Logitech",
    "g305": "Logitech",
    "g915": "Logitech",
    "superlight": "Logitech",
    "keychron": "Keychron",
    "razer": "Razer",
    "blackwidow": "Razer",
    "deathadder": "Razer",
    "corsair": "Corsair",
    "steelseries": "SteelSeries",
    "rival": "SteelSeries",
    "asus": "ASUS",
    "vivobook": "ASUS",
    "rog": "ASUS",
    "lenovo": "Lenovo",
    "ideapad": "Lenovo",
    "acer": "Acer",
    "aspire": "Acer",
    "xiaomi": "Xiaomi",
    "soundcore": "Anker",
    "anker": "Anker",
}


CATEGORY_RULES = {
    "Telefon": [
        "iphone", "galaxy", "pixel", "xiaomi", "phone"
    ],
    "Kulaklık": [
        "airpods", "wh-", "tune", "soundcore", "headphone", "kulaklık"
    ],
    "Laptop": [
        "macbook", "ideapad", "vivobook", "aspire", "laptop", "notebook"
    ],
    "Mouse": [
        "g305", "superlight", "deathadder", "rival", "mouse"
    ],
    "Klavye": [
        "keychron", "g915", "blackwidow", "k70", "keyboard", "klavye"
    ],
}


def slugify(text):
    text = text.lower().strip()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def detect_brand(name):
    text = name.lower()

    for keyword, brand in BRANDS.items():
        if keyword in text:
            return brand

    return ""


def detect_category(name):
    text = name.lower()

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return "Diğer"


def build_sources(name, brand):
    domain_map = {
        "Apple": "https://www.apple.com/",
        "Samsung": "https://www.samsung.com/",
        "Google": "https://store.google.com/",
        "Sony": "https://www.sony.com/",
        "JBL": "https://www.jbl.com/",
        "Logitech": "https://www.logitech.com/",
        "Keychron": "https://www.keychron.com/",
        "Razer": "https://www.razer.com/",
        "Corsair": "https://www.corsair.com/",
        "SteelSeries": "https://steelseries.com/",
        "ASUS": "https://www.asus.com/",
        "Lenovo": "https://www.lenovo.com/",
        "Acer": "https://www.acer.com/",
        "Xiaomi": "https://www.mi.com/",
        "Anker": "https://www.anker.com/",
    }

    return {
        "official_brand": domain_map.get(brand, ""),
        "search_query": f"{name} {brand} official specifications",
        "image_search_query": f"{name} official product image",
    }


def build_draft(name):
    brand = detect_brand(name)
    category = detect_category(name)
    slug = slugify(name)

    return {
        "product": {
            "name": name,
            "brand": brand,
            "category": category,
            "slug": slug,
        },

        "verification": {
            "brand": bool(brand),
            "exact_model": False,
            "official_source": False,
            "real_image": False,
            "technical_specs": False,
        },

        "sources": build_sources(name, brand),

        "image": {
            "url": "",
            "source": "",
            "verified": False,
        },

        "specs": {},

        "review": {
            "rating": None,
            "verdict": "",
            "description": "",
            "pros": [],
            "cons": [],
            "should_buy": "",
            "should_not_buy": "",
        },

        "seo": {
            "title": f"{name} İncelemesi | BURAK REVIEW",
            "description": (
                f"{name} teknik özellikleri, artıları, eksileri "
                f"ve detaylı BURAK REVIEW incelemesi."
            ),
        },

        "status": "DRAFT",

        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def save_research(data):
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    slug = data["product"]["slug"]
    path = RESEARCH_DIR / f"{slug}.json"

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return path


def print_preview(data, path):
    product = data["product"]
    verification = data["verification"]

    print()
    print("=" * 50)
    print("🔥 BURAK REVIEW — PRODUCT ENGINE")
    print("=" * 50)

    print()
    print("📦 ÜRÜN")
    print(f"   Ad       : {product['name']}")
    print(f"   Marka    : {product['brand'] or 'Bulunamadı'}")
    print(f"   Kategori : {product['category']}")
    print(f"   Slug     : {product['slug']}")

    print()
    print("🔐 DOĞRULAMA")
    print(
        f"   Marka           : "
        f"{'✅' if verification['brand'] else '❌'}"
    )
    print(
        f"   Exact model     : "
        f"{'✅' if verification['exact_model'] else '⏳'}"
    )
    print(
        f"   Resmî kaynak    : "
        f"{'✅' if verification['official_source'] else '⏳'}"
    )
    print(
        f"   Gerçek görsel   : "
        f"{'✅' if verification['real_image'] else '⏳'}"
    )
    print(
        f"   Teknik bilgiler : "
        f"{'✅' if verification['technical_specs'] else '⏳'}"
    )

    print()
    print("🔗 KAYNAK")
    print(f"   {data['sources']['official_brand']}")

    print()
    print("🔍 SEO")
    print(f"   {data['seo']['title']}")
    print(f"   {data['seo']['description']}")

    print()
    print("💾 ARAŞTIRMA DOSYASI")
    print(f"   {path}")

    print()
    print("⚠️ DURUM: ONAY BEKLİYOR")
    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print('Kullanım:')
        print('python tools/product_engine.py "iPhone 16"')
        raise SystemExit(1)

    name = " ".join(sys.argv[1:]).strip()

    if not name:
        print("❌ Ürün adı boş.")
        raise SystemExit(1)

    data = build_draft(name)
    path = save_research(data)

    print_preview(data, path)


if __name__ == "__main__":
    main()
