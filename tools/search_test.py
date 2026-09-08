import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.providers.search_provider import get_provider


def main():
    if len(sys.argv) < 2:
        print('Kullanım: python tools/search_test.py "iPhone 16"')
        raise SystemExit(1)

    query = " ".join(sys.argv[1:])

    provider = get_provider()

    if provider is None:
        print()
        print("⚠️ AKTİF ARAMA SAĞLAYICISI YOK")
        print()
        print("Şu anda motor hazır fakat SEARCH_PROVIDER ayarlanmamış.")
        print("Bu normal. Henüz API anahtarını sisteme koymadık.")
        return

    print()
    print("🔎 BURAK REVIEW — WEB SEARCH")
    print("=" * 45)
    print(f"Arama: {query}")
    print()

    try:
        results = provider.search(query)

    except Exception as exc:
        print("❌ Arama başarısız.")
        print(f"   Hata: {exc}")
        raise SystemExit(1)

    if not results:
        print("⚠️ Sonuç bulunamadı.")
        return

    for index, result in enumerate(results, 1):
        print(f"{index}. {result['title']}")
        print(f"   {result['url']}")
        print(f"   {result['snippet']}")
        print()


if __name__ == "__main__":
    main()
