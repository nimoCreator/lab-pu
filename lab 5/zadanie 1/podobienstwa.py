import math
from typing import List
import google.generativeai as genai

API_KEY = "AIzaSyBWoUQqQTEvx8gI7hD34Enl6AgV5WELe3g"

genai.configure(api_key=API_KEY)

EMBED_MODEL = "models/text-embedding-004"
OUTPUT_FILE = "podobienstwa.txt"

QUESTIONS: List[str] = [
    "Jaka jest najnowsza konsola od Valve?",
    "Co znaczy skrot TUC?",
    "W jakim miescie w Polsce sa najnizsze koszty wynajmu mieszkania?",
]

TEXTS: List[str] = [
    "Najnowsza konsola od Valve to Steam Deck",
    "Valve Frame",
    "Szczecin",
    "Bydgoszcz",
    "Teoria Ukladow Cyfrowych",
    "Targi Uchodzcow w Czestochowie",
    "Dioda LED blokuje przeplyw pradu w jednym kierunku",
]


def get_embedding(text: str) -> List[float]:
    resp = genai.embed_content(
        model=EMBED_MODEL,
        content=text,
        task_type="retrieval_document",
    )
    return resp["embedding"]


def dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(a: List[float]) -> float:
    return math.sqrt(dot(a, a))


def cosine_similarity(a: List[float], b: List[float]) -> float:
    na = norm(a)
    nb = norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)


def euclidean_distance(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


if __name__ == "__main__":
    sample = get_embedding("test")
    print("Embedding test OK")

    q_embs = [get_embedding(q) for q in QUESTIONS]
    t_embs = [get_embedding(t) for t in TEXTS]

    cos_matrix = [[cosine_similarity(q, t) for t in t_embs] for q in q_embs]
    euc_matrix = [[euclidean_distance(q, t) for t in t_embs] for q in q_embs]
    dot_matrix = [[dot(q, t) for t in t_embs] for q in q_embs]

    cos_best = [max(r[c] for r in cos_matrix) for c in range(len(TEXTS))]
    euc_best = [min(r[c] for r in euc_matrix) for c in range(len(TEXTS))]
    dot_best = [max(r[c] for r in dot_matrix) for c in range(len(TEXTS))]

    def write_table(f, title, matrix, best_vals, find_max=True):
        f.write(title + "\n")

        headers = ["Pytanie"] + [f"T{idx+1}" for idx in range(len(TEXTS))]

        rows = []
        for qi, row in enumerate(matrix):
            cells = []
            for ci, val in enumerate(row):
                val_s = f"{val:.4f}"
                if val == best_vals[ci]:
                    val_s = f"[{val_s}]"
                cells.append(val_s)
            rows.append([QUESTIONS[qi]] + cells)

        col_w = [len(h) for h in headers]
        for row in rows:
            for c in range(len(headers)):
                col_w[c] = max(col_w[c], len(row[c]))

        def border():
            return "+" + "+".join("-"*(w+2) for w in col_w) + "+\n"

        def line(vals):
            return "|" + "|".join(f" {v.ljust(w)} " for v, w in zip(vals, col_w)) + "|\n"

        f.write(border())
        f.write(line(headers))
        f.write(border())
        for r in rows:
            f.write(line(r))
        f.write(border())
        f.write("\n")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        f.write("TEKSTY (kolumny):\n")
        for i, t in enumerate(TEXTS, start=1):
            f.write(f" T{i}: {t}\n")
        f.write("\nPYTANIA (wiersze):\n")
        for i, q in enumerate(QUESTIONS, start=1):
            f.write(f" Q{i}: {q}\n")
        f.write("\n----------------------------------------------\n\n")

        write_table(f, "=== COSINE SIMILARITY ===", cos_matrix, cos_best)
        write_table(f, "=== EUCLIDEAN DISTANCE ===", euc_matrix, euc_best, find_max=False)
        write_table(f, "=== DOT PRODUCT ===", dot_matrix, dot_best)

    print("Zapisano:", OUTPUT_FILE)
