import os
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ksiazkaModel import Ksiazka

DATABASE_URL = "mssql+pyodbc://@(localdb)\\MSSQLLocalDB/Biblioteka?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

API = "https://gutendex.com/books/?page=1"

def fetch_books():
    r = requests.get(API, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])  

def main():
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    books = fetch_books()
    inserted = 0
    with Session(engine) as session:
        for b in books:
            title = b.get("title") or "(no title)"
            summaries = b.get("summaries") or []
            summary = summaries[0] if summaries else "(no summary)"

            exists = session.execute(
                select(Ksiazka.id).where(
                    Ksiazka.angielski_tytul == title,
                    Ksiazka.angielskie_streszczenie == summary,
                )
            ).scalar_one_or_none()
            if exists:
                continue

            session.add(
                Ksiazka(
                    angielski_tytul=title,
                    angielskie_streszczenie=summary,
                )
            )
            inserted += 1
        session.commit()
    print(f"Wstawiono {inserted} rekordow.")

if __name__ == "__main__":
    main()
