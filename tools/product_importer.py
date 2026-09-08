import json
import re
import sys
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_FILE = ROOT / "frontend" / "data" / "products.json"


def slugify(text):
    text = text.lower().strip()
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
    text = text.replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def load_products():
    if not PRODUCTS_FILE.exists():
        return []

    with PRODUCTS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("products.json bir liste olmalı.")

    return data


def guess_category(name):
    n = name.lower()

    if any(x in n for x in [
        "airpods", "headphone", "wh-", "tune", "buds", "kulaklık"
    ]):
        return "Kulaklık"

    if any(x in n for x in [
        "keyboard", "klavye", "k70", "k2", "g915", "blackwidow"
    ]):
        return "Klavye"

    if any(x in n for x in [
        "mouse", "g305", "deathadder", "rival", "superlight"
    ]):
        return "Mouse"

    if any(x in n for x in [
        "iphone", "galaxy", "pixel", "xiaomi"
    ]):
        return "Telefon"

    if any(x in n for x in [
        "macbook", "ideapad", "vivobook", "aspire", "laptop"
    ]):
        return "Laptop"

    return "Diğer"


def guess_brand(name):
    brands = [
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

    lower = name.lower()

    for brand in brands:
        if brand.lower() in lower:
            return brand

    return ""


def build_product(name):
    brand = guess_brand(name)
    category = guess_category(name)
    slug = slugify(name)

    return {
        "slug": slug,
        "name": name,
        "brand": brand,
        "category": category,
        "icon": "📦",
        "image": "",
        "price": "Güncel fiyat kontrol edilmeli",
        "rating": 0,
        "verdict": "İnceleme hazırlanıyor.",
        "description": "",
        "pros": [],
        "cons": [],
        "shouldBuy": "",
        "shouldNotBuy": "",
        "specs": {},
        "seo": {
            "title": f"{name} İncelemesi | BURAK REVIEW",
            "description": f"{name} teknik özellikleri, artıları, eksileri ve detaylı incelemesi."
        },
        "source": {
            "status": "Araştırma bekliyor",
            "verified": False,
            "checked_at": datetime.now().isoformat(timespec="seconds")
        }
    }


def print_preview(product):
    print()
    print("=" * 50)
    print("🔥 BURAK REVIEW PRODUCT IMPORTER")
    print("=" * 50)
    print()
    print(f"📦 Ürün      : {product['name']}")
    print(f"🏢 Marka     : {product['brand'] or 'Bulunamadı'}")
    print(f"📂 Kategori  : {product['category']}")
    print(f"🔗 Slug      : {product['slug']}")
    print()
    print("🔎 SEO")
    print(f"   Başlık    : {product['seo']['title']}")
    print(f"   Açıklama  : {product['seo']['description']}")
    print()
    print("🖼️ Görsel    : Henüz doğrulanmadı")
    print("📋 Bilgiler  : Henüz araştırılmadı")
    print("⚠️ Durum     : TASLAK")
    print()
    print("=" * 50)


def main():
    if len(sys.argv) < 2:
        print('Kullanım:')
        print('python tools/product_importer.py "Ürün Adı"')
        sys.exit(1)

    name = " ".join(sys.argv[1:]).strip()

    if not name:
        print("❌ Ürün adı boş olamaz.")
        sys.exit(1)

    products = load_products()

    slug = slugify(name)

    for product in products:
        if product.get("slug") == slug:
            print(f"⚠️ Bu ürün zaten katalogda: {product.get('name')}")
            sys.exit(0)

    product = build_product(name)

    print_preview(product)

    answer = input("Taslak olarak products.json'a eklensin mi? [e/h]: ").strip().lower()

    if answer not in ("e", "evet"):
        print("❌ İşlem iptal edildi.")
        return

    products.append(product)

    with PRODUCTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print()
    print("✅ Ürün taslak olarak eklendi.")
    print(f"📁 {PRODUCTS_FILE}")
    print(f"📊 Toplam ürün: {len(products)}")


if __name__ == "__main__":
    main()
