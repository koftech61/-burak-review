from urllib.parse import quote


BRAND_RULES = {
    "iphone": "Apple",
    "airpods": "Apple",
    "macbook": "Apple",
    "ipad": "Apple",

    "galaxy": "Samsung",

    "pixel": "Google",

    "wh-": "Sony",
    "bravia": "Sony",

    "tune": "JBL",

    "g305": "Logitech",
    "g915": "Logitech",
    "g pro": "Logitech",
    "superlight": "Logitech",

    "blackwidow": "Razer",
    "deathadder": "Razer",

    "k70": "Corsair",

    "rival": "SteelSeries",

    "vivobook": "ASUS",
    "rog": "ASUS",

    "ideapad": "Lenovo",

    "aspire": "Acer",

    "xiaomi": "Xiaomi",

    "soundcore": "Anker",
}


OFFICIAL_DOMAINS = {
    "Apple": "apple.com",
    "Samsung": "samsung.com",
    "Google": "store.google.com",
    "Sony": "sony.com",
    "JBL": "jbl.com",
    "Logitech": "logitech.com",
    "Razer": "razer.com",
    "Corsair": "corsair.com",
    "SteelSeries": "steelseries.com",
    "ASUS": "asus.com",
    "Lenovo": "lenovo.com",
    "Acer": "acer.com",
    "Xiaomi": "mi.com",
    "Anker": "anker.com",
}


def detect_brand(product_name):
    text = product_name.lower()

    for keyword, brand in BRAND_RULES.items():
        if keyword in text:
            return brand

    return ""


def build_official_search(product_name, brand):
    domain = OFFICIAL_DOMAINS.get(brand)

    if not domain:
        return None

    query = quote(f"{product_name} site:{domain}")

    return f"https://www.google.com/search?q={query}"


def build_research_profile(product_name):
    brand = detect_brand(product_name)

    return {
        "product": product_name,
        "brand": brand,
        "official_domain": OFFICIAL_DOMAINS.get(brand, ""),
        "official_search": build_official_search(
            product_name,
            brand
        ),
        "verification": {
            "brand": bool(brand),
            "official_source": False,
            "model": False,
            "image": False,
            "specs": False,
        },
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print('Kullanım: python tools/product_sources.py "Ürün Adı"')
        raise SystemExit(1)

    name = " ".join(sys.argv[1:])

    result = build_research_profile(name)

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ))
