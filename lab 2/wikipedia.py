import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from pathlib import Path
from baza import Tabela_Technika_jadrowa, Haslo

url = "https://pl.wikipedia.org/wiki/Kategoria:Technika_jądrowa"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Referer": "https://pl.wikipedia.org/",
}
connection_string = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=(localdb)\\MSSQLLocalDB;"
    "Database=Wikipedia;"
    "Trusted_Connection=yes;"
)

def getTresc(href: str) -> str:
    addres = "https://pl.wikipedia.org" + href

    response = requests.get(addres, headers=headers, timeout=20)

    if response.status_code != 200:
        print(f"oopsie: {response.status_code} -> {addres}")

    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    cont = soup.select_one(".mw-content-ltr.mw-parser-output") or soup

    for t in cont.find_all("table"):
            t.decompose()

    for p in cont.find_all("p"):
        text = p.get_text(" ", strip=True)
        text = re.sub(r"\[\s*(\d+|[a-zA-Z])(\s*[–\-]\s*(\d+|[a-zA-Z]))?\s*\]", "", text) 
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        if text:
            # print(text)
            return text
        
    return ""





# main

response = requests.get(url, headers=headers, timeout=20)
if response.status_code != 200:
    print(f"oopsie: {response.status_code}")
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

with Tabela_Technika_jadrowa(connection_string) as repo:
    repo.usun_wszystko()

    for a in soup.select("#mw-pages a"):
        href = a.get("href")
        title = a.get_text(strip=True)
        tresc = getTresc(href)
        repo.dodaj_haslo(Haslo(None, title, tresc))

    hasla = repo.pobierz_hasla()
    df = pd.DataFrame([h.__dict__ for h in hasla]).drop_duplicates(ignore_index=True)

    # outfile = Path("Wikipedia.txt")
    # with outfile.open("w", encoding="utf-8") as f:
    #     f.write(df.to_string(index=False))
    #     f.write("\n")
    # print(f"Zapisano {outfile.resolve()}")

    with open("Wikipedia.json", "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
    print("Zapisano Wikipedia.json")



