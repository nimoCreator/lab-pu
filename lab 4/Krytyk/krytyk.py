# krytyk.py
# -*- coding: utf-8 -*-
import re, json, time, pathlib
from datetime import datetime, timezone

from local_qwen import pytaj_Qwen
from gemini import pytaj_Gemini   

LOGS_DIR = pathlib.Path("./logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_TXT_PATH = LOGS_DIR / f"log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"

def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _now_local_str():
    return datetime.now().strftime("%H:%M:%S")

def _append_log_txt(entry: dict):
    entry["data_local"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with LOG_TXT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()

def _print_info(msg: str, t_start: float, t_last: float):
    now = time.perf_counter()
    delta = now - t_last
    total = now - t_start
    print(f"\033[90m[{_now_local_str()} | +{delta:.2f}s | total {total:.2f}s] {msg}\033[0m")
    return now

def pytaj_z_Krytykiem(pytanie: str, max_rounds: int = 5) -> str:
    """
    Pętla:
      1) Qwen odpowiada
      2) Gemini zwraca JSON: {"czy_korekta": bool, "sugestia": str}
      3) jeśli trzeba poprawić -> Qwen dostaje (pytanie, poprzednia odpowiedź, sugestie) i odpowiada ponownie
      4) koniec gdy czy_korekta == False lub osiągnięto max_rounds
    """
    review_sys = (
        "Zwracaj SCISLY JSON, BEZ komentarzy. Schemat:\n"
        '{ "czy_korekta": boolean, "sugestia": string }\n'
        "Oceniaj poprawnosc, scislosc i brak halucynacji. "
        "Jesli trzeba poprawic -> czy_korekta=true i w 'sugestia' podaj konkretne wskazowki. "
        "Jesli jest dobrze -> czy_korekta=false, a w 'sugestia' krotkie uzasadnienie."
    )

    print(f"📄 logowanie do pliku: {LOG_TXT_PATH}")
    print(f"Ty: {pytanie}")
    _append_log_txt({"ts": _now_iso(), "etap": "start", "pytanie": pytanie})

    t_start = time.perf_counter()
    t_last = t_start

    current_input = pytanie
    final_answer = None

    for r in range(1, max_rounds + 1):
        # 1) Qwen (lokalny) — UNPACK (odp, loc_dt)
        t_last = _print_info(f"→ przekazano pytanie do Qwen (runda {r})", t_start, t_last)
        odp, loc_dt = pytaj_Qwen(current_input)
        t_last = _print_info("✔ Qwen odpowiedzial", t_start, t_last)
        _append_log_txt({
            "ts": _now_iso(),
            "etap": "lokalna_odpowiedz",
            "runda": r,
            "wejscie": current_input,
            "odpowiedz": odp,
            "latency_s": loc_dt,
        })

        # 2) Gemini review (prostota: Gemini zwraca str; mierzymy czas lokalnie)
        t_last = _print_info("→ przekazano do recenzji Gemini", t_start, t_last)
        t_gem0 = time.perf_counter()
        contents_for_review = (
            review_sys
            + "\n\nPYTANIE:\n" + pytanie
            + "\n\nODP_LOCAL:\n" + odp
        )
        txt = pytaj_Gemini(contents_for_review)
        gem_dt = round(time.perf_counter() - t_gem0, 3)
        t_last = _print_info("✔ Gemini zwrocil recenzje", t_start, t_last)

        raw = txt.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.DOTALL).strip()

        try:
            review = json.loads(raw)
        except Exception:
            review = {"czy_korekta": True, "sugestia": "Nie udalo sie sparsowac JSON."}

        need_fix = bool(review.get("czy_korekta", True))
        _append_log_txt({
            "ts": _now_iso(),
            "etap": "gemini_recenzja",
            "runda": r,
            "review": review,
            "latency_s": gem_dt,
        })

        if not need_fix:
            final_answer = odp
            break

        # 3) poprawka – nowy prompt dla Qwen z sugestią
        sugestia = (review.get("sugestia") or "").strip()
        current_input = (
            f"{pytanie}\n\n"
            f"Twoja poprzednia odpowiedz:\n{odp}\n\n"
            f"Ulepsz odpowiedz zgodnie z sugestiami recenzenta:\n{sugestia}\n\n"
            f"Odpowiedz krotko i poprawnie."
        )

    if final_answer is None:
        final_answer = "(Nie uzyskano akceptu w limicie iteracji.)"

    print(f"✅ Model: {final_answer}")
    _append_log_txt({"ts": _now_iso(), "etap": "final", "final_answer": final_answer})
    return final_answer

if __name__ == "__main__":
    maxRund = int(input("Podaj maksymalna liczbe rund Krytyka (np. 5): ") or "5")
    pytanie = input("Podaj pytanie do Krytyka: ")
    wynik = pytaj_z_Krytykiem(pytanie, max_rounds=maxRund)
    print("Wynik koncowy:", wynik)
    print("Log:", str(LOG_TXT_PATH.resolve()))
