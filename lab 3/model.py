import os
import time
import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from ksiazkaModel import Ksiazka

DATABASE_URL = "mssql+pyodbc://@(localdb)\MSSQLLocalDB/Biblioteka?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_ID = "Qwen/Qwen3-VL-235B-A22B-Instruct:novita"
HF_TOKEN = "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"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else None

def translate_text(text_en: str) -> str:
    if not text_en:
        return ""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Translate the following text into Polish. In your response output ONLY the translation without any additional text, explanations, or quotes."
                    },
                    {"type": "text", "text": text_en},
                ],
            }
        ],
    }
    r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        print("⚠️ Nieoczekiwany ksztalt odpowiedzi:", data)
        return ""

def main():
    if not HEADERS:
        raise RuntimeError("Brak tokena. Ustaw HF_TOKEN w srodowisku.")

    engine = create_engine(DATABASE_URL, echo=False, future=True)

    with Session(engine) as session:
        q = select(Ksiazka)
        books = session.scalars(q).all()
        print(f"Znaleziono {len(books)} ksiazek w bazie.")

        for i, book in enumerate(books, 1):
            changed = False
            print(f"[{i}/{len(books)}] Przetwarzam: {book.angielski_tytul[:60]}...")

            if not book.polski_tytul:
                book.polski_tytul = translate_text(book.angielski_tytul)
                changed = True

            if not book.polskie_streszczenie:
                book.polskie_streszczenie = translate_text(book.angielskie_streszczenie)
                changed = True

            if changed:
                session.commit()
                time.sleep(0.4)

    print("✅ Zakonczono tlumaczenia i aktualizacje w bazie.")

if __name__ == "__main__":
    main()
