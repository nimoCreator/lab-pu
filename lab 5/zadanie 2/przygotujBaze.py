
import json
from typing import List
import pyodbc
import google.generativeai as genai

CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=(localdb)\MSSQLLocalDB;DATABASE=BazaWiedzy;"


GEMINI_API_KEY = "AIzaSyBWoUQqQTEvx8gI7hD34Enl6AgV5WELe3g"
genai.configure(api_key=GEMINI_API_KEY)

EMBED_MODEL = "models/text-embedding-004"

TEXTS: List[str] = [
    "Newest vr headset annouced by Valve is Steam Frame",
    "Currently the president of the United States is Donald Trump",
    "TUC stands for Troria Układów Cyfrowych",    
]


def get_embedding(text: str) -> List[float]:
    resp = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return resp["embedding"]


if __name__ == "__main__":
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute(
        """
        IF NOT EXISTS (
            SELECT * FROM sys.objects
            WHERE object_id = OBJECT_ID(N'[dbo].[KnowledgeBase]')
            AND type in (N'U')
        )
        BEGIN
            CREATE TABLE [dbo].[KnowledgeBase] (
                [id] INT IDENTITY(1,1) PRIMARY KEY,
                [text] NVARCHAR(MAX) NOT NULL,
                [embedding] NVARCHAR(MAX) NOT NULL
            );
        END
        """
    )
    conn.commit()

    for txt in TEXTS:
        emb = get_embedding(txt)
        emb_json = json.dumps(emb) 

        cursor.execute(
            "INSERT INTO [dbo].[KnowledgeBase] ([text], [embedding]) VALUES (?, ?)",
            txt,
            emb_json,
        )

    conn.commit()
    cursor.close()
    conn.close()

    print("Baza KnowledgeBase przygotowana i wypelniona embeddingami.")
