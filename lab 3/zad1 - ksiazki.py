import requests

URL = "https://gutendex.com/books?page=1" 

def main():
    result = requests.get(URL, timeout=30)
    result.raise_for_status()
    data = result.json()
    for book in data.get("results", []):
        title = book.get("title", "(brak tytulu)")
        summaries = book.get("summaries", []) or []
        print(title)
        print(summaries)

if __name__ == "__main__":
    main()
