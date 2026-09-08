import json
import sys
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / "tools" / "research"


def save_research(result):
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    slug = result["product"]["slug"]

    path = RESEARCH_DIR / f"{slug}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    return path


def build_result(
    name,
    brand,
    category,
    slug,
    official_source="",
    image_url="",
    specs=None,
):
    return {
        "product": {
            "name": name,
            "brand": brand,
            "category": category,
            "slug": slug,
        },

        "verification": {
            "brand_verified": bool(brand),
            "model_verified": False,
            "official_source_verified": bool(official_source),
            "image_verified": bool(image_url),
            "specs_verified": bool(specs),
        },

        "sources": {
            "official": official_source,
            "image": image_url,
            "additional": [],
        },

        "image": {
            "url": image_url,
            "status": "verified" if image_url else "pending",
        },

        "specs": specs or {},

        "review": {
            "rating": None,
            "verdict": "",
            "description": "",
            "pros": [],
            "cons": [],
            "shouldBuy": "",
            "shouldNotBuy": "",
        },

        "seo": {
            "title": f"{name} İncelemesi | BURAK REVIEW",
            "description": (
                f"{name} teknik özellikleri, "
                f"artıları, eksileri ve detaylı BURAK REVIEW incelemesi."
            ),
        },

        "status": "DRAFT",

        "created_at": datetime.now().isoformat(
            timespec="seconds"
        ),
    }


def print_result(result):
    product = result["product"]
    verification = result["verification"]

    print()
    print("=" * 60)
    print("🔥 BURAK REVIEW — ARAŞTIRMA SONUCU")
    print("=" * 60)

    print()
    print("📦 ÜRÜN")
    print(f"   Ad      : {product['name']}")
    print(f"   Marka   : {product['brand']}")
    print(f"   Kategori: {product['category']}")
    print(f"   Slug    : {product['slug']}")

    print()
    print("🔐 DOĞRULAMA")
    print(
        f"   Marka        : "
        f"{'✅' if verification['brand_verified'] else '❌'}"
    )
    print(
        f"   Model        : "
        f"{'✅' if verification['model_verified'] else '⏳'}"
    )
    print(
        f"   Resmî kaynak : "
        f"{'✅' if verification['official_source_verified'] else '⏳'}"
    )
    print(
        f"   Görsel       : "
        f"{'✅' if verification['image_verified'] else '⏳'}"
    )
    print(
        f"   Teknik bilgi : "
        f"{'✅' if verification['specs_verified'] else '⏳'}"
    )

    print()
    print("🖼️ GÖRSEL")
    print(
        result["image"]["url"]
        if result["image"]["url"]
        else "   Henüz doğrulanmadı."
    )

    print()
    print("🔗 RESMÎ KAYNAK")
    print(
        result["sources"]["official"]
        if result["sources"]["official"]
        else "   Henüz doğrulanmadı."
    )

    print()
    print("📋 TEKNİK ÖZELLİKLER")

    if result["specs"]:
        for key, value in result["specs"].items():
            print(f"   • {key}: {value}")
    else:
        print("   Henüz doğrulanmadı.")

    print()
    print("🔍 SEO")
    print(f"   {result['seo']['title']}")
    print(f"   {result['seo']['description']}")

    print()
    print("⚠️ DURUM:", result["status"])

    print("=" * 60)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print(
            'Kullanım:\n'
            'python tools/research_result.py '
            '"Ürün" "Marka" "Kategori" "Slug"'
        )
        sys.exit(1)

    name = sys.argv[1]
    brand = sys.argv[2]
    category = sys.argv[3]
    slug = sys.argv[4]

    result = build_result(
        name=name,
        brand=brand,
        category=category,
        slug=slug,
    )

    path = save_research(result)

    print_result(result)

    print(f"💾 Araştırma taslağı kaydedildi:")
    print(f"   {path}")
