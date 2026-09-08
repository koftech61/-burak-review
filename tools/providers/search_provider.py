import json
import os
import urllib.parse
import urllib.request


class SearchProvider:
    """
    BURAK REVIEW için arama sağlayıcısı arayüzü.

    Daha sonra gerçek bir API sağlayıcısı buraya takılabilir.
    """

    def search(self, query, max_results=10):
        raise NotImplementedError


class GoogleWebSearchProvider(SearchProvider):

    ENDPOINT = "https://websearchservice.googleapis.com/v1:search"

    def __init__(self, api_key, client_id):
        self.api_key = api_key
        self.client_id = client_id

    def search(self, query, max_results=10):
        params = {
            "searchQuery.query": query,
            "clientContext.clientId": self.client_id,
            "userContext.regionCode": "TR",
            "searchQuery.languageCode": "tr",
            "pageSize": min(max_results, 20),
        }

        url = self.ENDPOINT + "?" + urllib.parse.urlencode(params)

        request = urllib.request.Request(
            url,
            headers={
                "X-Goog-Api-Key": self.api_key,
                "Accept": "application/json",
            },
            method="GET",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []

        for item in data.get("searchResults", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("displayUrl", ""),
                "snippet": item.get("snippet", ""),
            })

        return results


def get_provider():
    provider = os.getenv("SEARCH_PROVIDER", "").strip().lower()

    if provider == "google":
        api_key = os.getenv("SEARCH_API_KEY", "").strip()
        client_id = os.getenv("SEARCH_CLIENT_ID", "").strip()

        if not api_key:
            raise RuntimeError("SEARCH_API_KEY eksik.")

        if not client_id:
            raise RuntimeError("SEARCH_CLIENT_ID eksik.")

        return GoogleWebSearchProvider(
            api_key=api_key,
            client_id=client_id,
        )

    return None
