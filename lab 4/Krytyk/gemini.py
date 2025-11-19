import os
import json
import time
import pathlib
import requests
from datetime import datetime, timezone

API_KEY = "AIzaSyDxEDC3E7G8oUIJPrcKOGNdrddM6AcSaCw"
MODEL_NAME = "gemini-2.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"

LOG_DIR = pathlib.Path("./logs_gemini")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

SYSTEM_PROMPT = "Jestes pomocnym asystentem. Odpowiadaj krotko i rzeczowo, po polsku."
GEN_CFG = {"temperature": 0.7, "topP": 0.9}

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def append_log(role: str, content: str, meta: dict | None = None) -> None:
    entry = {"ts": now_iso(), "role": role, "content": content}
    if meta:
        entry.update(meta)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()  # flush so logs appear live

def print_info(msg: str) -> None:
    print(f"\033[90m{msg}\033[0m")

def pytaj_Gemini(prompt: str, history: list[dict] | None = None, system_prompt: str | None = None) -> str:
    if not API_KEY:
        raise RuntimeError("Brak GEMINI_API_KEY. Dodaj do .env lub zmiennych srodowiskowych.")
    system_prompt = system_prompt or SYSTEM_PROMPT
    history = history or []

    contents = []
    if system_prompt:
        contents.append({"role": "user", "parts": [{"text": system_prompt}]})

    for msg in history:
        role = msg["role"]
        if role == "system":
            role = "user"
        elif role == "assistant":
            role = "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {"contents": contents, "generationConfig": GEN_CFG}

    t0 = time.perf_counter()
    resp = requests.post(API_URL, json=payload, timeout=120)
    dt = round(time.perf_counter() - t0, 3)

    if not resp.ok:
        append_log("assistant", f"HTTP {resp.status_code}: {resp.text}", {"error": True})
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        text = "[blad parsowania odpowiedzi API]"

    append_log("user", prompt)
    append_log("assistant", text, {"latency_s": dt})
    return text

if __name__ == "__main__":
    print_info(f"Log do pliku: {LOG_FILE}")
    ans = pytaj_Gemini("Powiedz jedno zdanie o pogodzie w Krakowie (bez wstepu).")
    print("Gemini:", ans)
