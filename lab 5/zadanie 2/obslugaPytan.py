import json
import math
from typing import List, Tuple

import pyodbc
import google.generativeai as genai
from llama_cpp import Llama


CONN_STR = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=(localdb)\\MSSQLLocalDB;DATABASE=BazaWiedzy;"

GEMINI_API_KEY = "AIzaSyBWoUQqQTEvx8gI7hD34Enl6AgV5WELe3g"
genai.configure(api_key=GEMINI_API_KEY)
EMBED_MODEL = "models/text-embedding-004"

QWEN_MODEL_PATH = "P:\\lab-pu\\lab 5\\zadanie 2\\model\\Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
RAG_LOG_FILE = "efektRAG.txt"


def get_embedding(text: str) -> List[float]:
    resp = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_query",
    )
    return resp["embedding"]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def load_knowledge_base() -> List[Tuple[int, str, List[float]]]:
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    cursor.execute("SELECT [id], [text], [embedding] FROM [dbo].[KnowledgeBase]")
    rows = cursor.fetchall()

    data: List[Tuple[int, str, List[float]]] = []
    for row in rows:
        emb_list = json.loads(row.embedding)
        data.append((row.id, row.text, emb_list))

    cursor.close()
    conn.close()
    return data


def find_best_match(question_emb: List[float], kb: List[Tuple[int, str, List[float]]]) -> Tuple[int, str, float]:
    best_id = -1
    best_text = ""
    best_score = -1.0

    for row_id, txt, emb in kb:
        score = cosine_similarity(question_emb, emb)
        if score > best_score:
            best_score = score
            best_id = row_id
            best_text = txt

    return best_id, best_text, best_score


def build_rag_prompt(user_question: str, context_text: str) -> str:
    return (
        "You are a helpful assistant.\n"
        "You must answer the user's question ONLY using the information from the context below.\n"
        "If the context does not contain the answer, say that the information is not available.\n\n"
        "Context:\n"
        f"{context_text}\n\n"
        "User question:\n"
        f"{user_question}\n\n"
        "Answer based ONLY on the context above:\n"
    )


if __name__ == "__main__":
    while True:
        user_question = input("You: ").strip()
        if not user_question:
            print("Empty question. Exiting.")
            raise SystemExit

        q_emb = get_embedding(user_question)

        kb = load_knowledge_base()
        if not kb:
            print("KnowledgeBase is empty.")
            raise SystemExit

        best_id, best_text, best_score = find_best_match(q_emb, kb)
        print(f"Best match id={best_id}, score={best_score:.4f}")
        print("Context text:\n", best_text)

        prompt = build_rag_prompt(user_question, best_text)

        llm = Llama(
            model_path=QWEN_MODEL_PATH,
            n_ctx=4096,
            n_threads=4,
        )

        output = llm(
            prompt,
            max_tokens=256,
            temperature=0.7,
            top_p=0.9,
        )
        answer = output["choices"][0]["text"].strip()

        print("\n=== RAG ANSWER ===")
        print(answer)

        with open(RAG_LOG_FILE, "a", encoding="utf-8") as f:
            f.write("========================================\n")
            f.write(f"QUESTION: {user_question}\n\n")
            f.write("CONTEXT USED:\n")
            f.write(best_text + "\n\n")
            f.write("MODEL ANSWER:\n")
            f.write(answer + "\n\n")

        print(f"\nZapisano przyklad do {RAG_LOG_FILE}")
