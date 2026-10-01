import json
import re
import sys
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent


BRANDS = [
    "Apple",
    "Samsung",
    "Sony",
    "JBL",
    "Logitech",
    "Keychron",
    "Razer",
    "Corsair",
    "SteelSeries",
    "Anker",
    "Soundcore",
    "Lenovo",
    "ASUS",
    "Acer",
    "Google",
    "Xiaomi",
]


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
    lower = name.lower()

    for brand in BRANDS:
        if brand.lower() in lower:
            return brand

    return ""


def detect_category(name):
    lower = name.lower()

    groups = {
        "Kulaklık": [
            "airpods",
            "headphone",
            "wh-",
            "tune",
            "buds",
            "kulaklık",
        ],
        "Klavye": [
            "keyboard",
            "klavye",
            "k70",
            "k2",
            "g915",
            "blackwidow",
        ],
        "Mouse": [
            "mouse",
            "g305",
            "deathadder",
            "rival",
            "superlight",
        ],
        "Telefon": [
            "iphone",
            "galaxy",
            "pixel",
            "xiaomi",
        ],
        "Laptop": [
            "macbook",
            "ideapad",
            "vivobook",
            "aspire",
            "laptop",
        ],
    }

    for category, keywords in groups.items():
        if any(keyword in lower for keyword in keywords):
            return category

    return "Diğer"


def build_search_links(product_name, brand):
    encoded = quote(product_name)

    links = [
        {
            "type": "Google Search",
            "url": f"https://www.google.com/search?q={encoded}",
        }
    ]

    if brand:
        links.append(
            {
                "type": "Official site search",
                "url": f"https://www.google.com/search?q={quote(brand + ' ' + product_name)}",
            }
        )

    return links


def research_product(name):
    brand = detect_brand(name)
    category = detect_category(name)
    slug = slugify(name)

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "slug": slug,
        "research_status": "MANUEL DOĞRULAMA BEKLİYOR",
        "official_source": "",
        "image_source": "",
        "sources": build_search_links(name, brand),
        "specs": {},
        "description": "",
        "pros": [],
        "cons": [],
        "seo": {
            "title": f"{name} İncelemesi | BURAK REVIEW",
            "description": (
                f"{name} incelemesi, teknik özellikleri, "
                "artıları, eksileri ve satın alma rehberi."
            ),
        },
    }


def print_result(product):
    print()
    print("=" * 55)
    print("🔥 BURAK REVIEW — PRODUCT RESEARCHER V2")
    print("=" * 55)

    print()
    print(f"📦 Ürün       : {product['name']}")
    print(f"🏢 Marka      : {product['brand'] or 'Bulunamadı'}")
    print(f"📂 Kategori   : {product['category']}")
    print(f"🔗 Slug       : {product['slug']}")

    print()
    print("🔎 ARAŞTIRMA KAYNAKLARI")

    for source in product["sources"]:
        print(f"   • {source['type']}")
        print(f"     {source['url']}")

    print()
    print("🖼️ Görsel     : Doğrulama bekliyor")
    print("📋 Teknik     : Doğrulama bekliyor")
    print("🏢 Resmî kaynak: Doğrulama bekliyor")

    print()
    print("🔍 SEO")
    print(f"   {product['seo']['title']}")
    print(f"   {product['seo']['description']}")

    print()
    print("⚠️ DURUM: TASLAK")
    print("=" * 55)
    print()


def main():
    if len(sys.argv) < 2:
        print('Kullanım: python tools/product_researcher.py "Ürün Adı"')
        sys.exit(1)

    name = " ".join(sys.argv[1:]).strip()

    if not name:
        print("❌ Ürün adı boş.")
        sys.exit(1)

    product = research_product(name)

    print_result(product)


if __name__ == "__main__":
    main()
