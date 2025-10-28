import os
import time
from huggingface_hub import InferenceClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from mymodel import Ksiazka

DATABASE_URL = "mssql+pyodbc://@(localdb)\MSSQLLocalDB/Biblioteka?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "Qwen/Qwen3-235B-A22B"

def translate_text(client: InferenceClient, text_en: str) -> str:
    if not text_en:
        return ""
    prompt = (
        "Translate the following text into Polish. Return ONLY the pure translation, "
        "without any comments, quotes or extra text:\n\n"
        f"{text_en}"
    )
    out = client.text_generation(
        model=MODEL_ID,
        prompt=prompt,
        max_new_tokens=800,
        temperature=0.2,
        top_p=0.9,
        repetition_penalty=1.05,
    )
    return (out or "").strip()

def main():
    if not HF_TOKEN:
        raise RuntimeError("Set HF_TOKEN environment variable to your Hugging Face write token.")
    client = InferenceClient(token=HF_TOKEN)

    engine = create_engine(DATABASE_URL, echo=False, future=True)
    updated = 0

    with Session(engine) as session:
        q = select(Ksiazka).where(
            (Ksiazka.polski_tytul.is_(None)) | (Ksiazka.polski_tytul == "") |
            (Ksiazka.polskie_streszczenie.is_(None)) | (Ksiazka.polskie_streszczenie == "")
        )
        for book in session.scalars(q):
            if not book.polski_tytul:
                book.polski_tytul = translate_text(client, book.angielski_tytul)
                time.sleep(0.2)

            if not book.polskie_streszczenie:
                book.polskie_streszczenie = translate_text(client, book.angielskie_streszczenie)
                time.sleep(0.2)

            updated += 1

        session.commit()

    print(f"Zaktualizowano {updated} rekordow.")

if __name__ == "__main__":
    main()
