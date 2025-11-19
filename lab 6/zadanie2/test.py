import requests
from urllib.parse import urlparse

def znajdzStony(haslo: str, limit: int = 5) -> list[dict]:
    """
    Korzysta z darmowego API DuckDuckGo (Instant Answer API),
    aby znalezc strony pasujace do podanego hasla.
    Zwraca liste obiektow: {"url": ..., "opis": ...},
    gdzie url jest MOZLIWIE docelowym adresem (po przekierowaniu).
    """
    base_url = "https://api.duckduckgo.com/"
    params = {
        "q": haslo,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
        "skip_disambig": 1,
    }
    resp = requests.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []

    def resolve_duckduckgo_url(url: str) -> str:
        """
        Jesli url wskazuje na duckduckgo.com/<cos>, probujemy wykonac GET
        i zwrocic finalny adres po przekierowaniach (np. Wikipedia).
        Jesli cos pojdzie nie tak – zwracamy oryginalny url.
        """
        try:
            parsed = urlparse(url)
            if "duckduckgo.com" not in parsed.netloc:
                return url  # to juz jest zewnetrzna strona

            r = requests.get(url, timeout=10, allow_redirects=True)
            return r.url or url
        except Exception:
            return url

    def add_item(item: dict):
        nonlocal results
        if "FirstURL" in item and "Text" in item:
            raw_url = item["FirstURL"]
            final_url = resolve_duckduckgo_url(raw_url)
            results.append({
                "url": final_url,
                "opis": item["Text"],
            })

    # 1) Bezposrednie wyniki
    for item in data.get("Results", []):
        add_item(item)
        if len(results) >= limit:
            return results

    # 2) RelatedTopics (zagniezdzone)
    def extract_topics(topics):
        for item in topics:
            if "FirstURL" in item and "Text" in item:
                add_item(item)
                if len(results) >= limit:
                    return
            if "Topics" in item:
                extract_topics(item["Topics"])
                if len(results) >= limit:
                    return

    extract_topics(data.get("RelatedTopics", []))
    return results

if __name__ == "__main__":
    haslo = input("Podaj haslo do wyszukania: ")
    strony = znajdzStony(haslo, limit=3)
    for strona in strony:
        print(f"- {strona['url']}: {strona['opis']}")
    if not strony:
        print("Brak wynikow")
    print()
