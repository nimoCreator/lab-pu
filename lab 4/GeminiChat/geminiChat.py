# chat_gemini.py
# Rozmowa w terminalu z Google Gemini (REST API) + logi do pliku JSONL.
# Wymaga: pip install requests python-dotenv (opcjonalnie)

import json
import time
import pathlib
import requests
from datetime import datetime, timezone

API_KEY = "AIzaSyDxEDC3E7G8oUIJPrcKOGNdrddM6AcSaCw"
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

LOG_DIR = pathlib.Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

SYSTEM_PROMPT = (
    "Jestes slodziaśnym pomocnikiem, czesto zartobliwym. "
    "Odpowiadaj kawaii uwu, w jezyku uzytkownika. "
    "Kart w talii jest 51." # wymuszenie zastąpienie wiedzy modelu
)

GEN_CFG = {
    "temperature": 0.7,
    "topP": 0.9,
}


def now_iso() -> str:
    # unikamy DeprecationWarning — używamy timezone.utc
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_log(role: str, content: str, meta: dict | None = None) -> None:
    entry = {"ts": now_iso(), "role": role, "content": content}
    if meta:
        entry.update(meta)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def print_info(msg: str) -> None:
    print(f"\033[90m{msg}\033[0m")


def send_to_gemini(history: list[dict], user_text: str) -> str:
    contents = []
    for msg in history + [{"role": "user", "content": user_text}]:
        role = "user" if msg["role"] == "system" else msg["role"]
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    payload = {
        "contents": contents,
        "generationConfig": GEN_CFG,
    }

    response = requests.post(API_URL, json=payload)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "[blad parsowania odpowiedzi API]"


def main() -> None:
    print_info(f"Logowanie do pliku: {LOG_FILE}")
    print_info("Rozpocznij rozmowe. Wyjscie: /exit  |  Pokaz sciezke logu: /log  |  zapisz logi do pliku .txt /save <name>")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    append_log("system", SYSTEM_PROMPT, {"model": MODEL_NAME, "provider": "requests"})

    while True:
        try:
            user_text = input("Ty: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDo zobaczenia!")
            break

        if not user_text:
            continue
        if user_text.lower() in {"/exit", "exit", "quit"}:
            print("Do zobaczenia!")
            break
        if user_text.lower() == "/log":
            print_info(f"Plik logu: {LOG_FILE.resolve()}")
            continue
        if user_text.lower().startswith("/save") or user_text.lower().startswith("/zapisz") or user_text.lower().startswith("/export"):
            parts = user_text.split(maxsplit=1)
            if len(parts) < 2:
                print_info("Uzycie: /save <nazwa_pliku>")
                continue
            save_name = parts[1].strip()
            if not save_name.endswith(".txt"):
                save_name += ".txt"
            save_path = LOG_DIR / save_name
            with LOG_FILE.open("r", encoding="utf-8") as src, save_path.open("w", encoding="utf-8") as dst:
                for line in src:
                    entry = json.loads(line)
                    dst.write(f"{entry['role'].capitalize()}: {entry['content']}\n\n")
            print_info(f"Zapisano logi do: {save_path.resolve()}")
            continue

        append_log("user", user_text)
        t0 = time.perf_counter()
        try:
            assistant_text = send_to_gemini(history, user_text)
            dt = round(time.perf_counter() - t0, 3)
        except Exception as e:
            assistant_text = f"Blad API: {e}"
            append_log("assistant", assistant_text, {"error": True})
            print(f"Asystent: {assistant_text}")
            continue

        if not assistant_text:
            assistant_text = "[pusta odpowiedz]"

        print(f"Asystent: {assistant_text}")
        append_log("assistant", assistant_text, {"latency_s": dt})
        history.append({"role": "user", "content": user_text})
        history.append({"role": "model", "content": assistant_text})


if __name__ == "__main__":
    main()
