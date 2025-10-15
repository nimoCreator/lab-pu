import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from pathlib import Path

def polskie_nazwisko(nazwisko: str) -> bool:
    """
    Funkcja testuje czy string zawieta polskie znaki

    :param nazwisko: podany string do testu
    :return: infromacja czy w podanym stringu wystepuja polskie litery
    """
    return bool(re.search(r"ąćęłńóśżźĄĆĘŁŃÓŚŻŹ", nazwisko))

def czyWieloczlonowe(text: str) -> bool:
    """
    Funkcja testuje czy string jest wieloczlonowy, poprzez sprawdzenie czy zawiera on spacje lub -

    :param text: podany string do testu
    :return: infromacja czy podany string jest wieloczlonowy
    """
    return bool(re.search(r"[ -]", text.strip()))

url = 'https://www.sejm.gov.pl/Sejm10.nsf/poslowie.xsp'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.senat.gov.pl/",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Referer": "https://www.sejm.gov.pl/",
}

response = requests.get(url, headers=headers, timeout=15)

if response.status_code != 200:
    print(f"oopsie: {response.status_code}")

response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

poslowie = []
for div in soup.find_all("div", class_="deputyName notranslate"):
    posel = div.get_text(strip=True)
    parts = posel.split()
    nazwisko = parts[0]
    imie = " ".join(parts[1:])
    poslowie.append({
        "imie": imie,
        "nazwisko": nazwisko,
        "plec": "k" if re.search(r"a$", imie, re.IGNORECASE) and not re.match(r"^(kuba|barnaba|kosma|bonawentura|jarema)$", imie, re.IGNORECASE) else "m",
        "polskie_znaki": polskie_nazwisko(nazwisko),
        "wieloczlonowe_imie": czyWieloczlonowe(imie),
        "wieloczlonowe_nazwisko": czyWieloczlonowe(nazwisko),
    })

df = pd.DataFrame(poslowie)
df = df.drop_duplicates(ignore_index=True)
print(df)


outfile = Path("poslowie.txt")
with outfile.open("w", encoding="utf-8") as f:
    f.write("\n=====[ POSLOWIE ]=====\n")
    f.write(f"Lacznie: {liczba_wszystkich}\n")
    f.write(f"Kobiety: {liczba_k}\n")
    f.write(f"Mezczyzni: {liczba_m}\n")
    f.write(f"Z polskimi znakami w nazwisku: {liczba_polskie}\n")
    f.write(f"Wieloczlonowe imie: {liczba_wielo_imie}\n")
    f.write(f"Wieloczlonowe nazwisko: {liczba_wielo_nazw}\n")
    f.write("\n\n\nimie\tnazwisko\tplec\tpolskie_znaki\twieloczlonowe_imie\twieloczlonowe_nazwisko\n")
    df.to_csv(f, sep="\t", index=False, header=False)
print(f"Zapisano {outfile.resolve()}")