import json
import time
import pathlib
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

API_KEY = "AIzaSyBWoUQqQTEvx8gI7hD34Enl6AgV5WELe3g"
SERPAPI_KEY = "568b20408525ca022ba03107324ed0dbd5bdfb04fc3fcedb15d3715f659a025b"

MODEL_NAME = "gemini-2.5-flash"
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
)

# =================== Logging ===================
LOG_DIR = pathlib.Path(".")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "logFC_z2.txt"

SYSTEM_PROMPT = (
    "Jestes pomocnym asystentem. "
    "Masz dostep do funkcji, ktore pozwalaja pobrac aktualna date i czas oraz ceny i strony internetowe. "
    "Jezeli uzyjesz funkcji, opisz w odpowiedzi skad dane pochodza. "
    "Jezeli uzytkownik pyta o informacje z internetu, najpierw wyszukaj strony, a nastepnie na podstawie ich opisow odpowiedz."
)

GEN_CFG = {"temperature": 0.7, "topP": 0.9}


# =================== Tools ===================

def pobierzDateCzas() -> str:
    teraz = datetime.now()
    return teraz.strftime("%Y-%m-%d %H:%M:%S")


def pobierzCeneBitcoin(waluta: str = "usd") -> float:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={waluta}"
    resp = requests.get(url, timeout=10)
    dane = resp.json()
    return dane["bitcoin"][waluta]


def znajdzStony(haslo: str, limit: int = 5) -> list[dict]:
    """
    Korzysta z SerpApi DuckDuckGo Search API
    Zwraca listę [{"url": ..., "opis": ...}]
    """
    if not haslo:
        return []

    url = "https://serpapi.com/search"
    params = {
        "engine": "duckduckgo",
        "q": haslo,
        "api_key": SERPAPI_KEY,
        "kl": "pl-pl"
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic_results", []):
        link = item.get("link")
        snippet = item.get("snippet") or item.get("title")
        if link and snippet:
            results.append({"url": link, "opis": snippet})
            if len(results) >= limit:
                break

    return results


def pobierzStrone(url: str) -> str:
    resp = requests.get(url, timeout=10)
    return resp.text


DATE_TIME_FUNCTION_DECL = {
    "name": "pobierzDateCzas",
    "description": "Zwraca aktualna date i czas w formacie tekstowym.",
    "parameters": {"type": "object", "properties": {}}
}

BTC_PRICE_FUNCTION_DECL = {
    "name": "pobierzCeneBitcoin",
    "description": "Zwraca aktualna cene Bitcoina w podanej walucie.",
    "parameters": {
        "type": "object",
        "properties": {"waluta": {"type": "string"}},
        "required": []
    }
}

FIND_SITES_FUNCTION_DECL = {
    "name": "znajdzStony",
    "description": "Wyszukuje strony na podstawie hasla i zwraca URL + krotki opis.",
    "parameters": {
        "type": "object",
        "properties": {
            "haslo": {"type": "string"},
            "limit": {"type": "integer"}
        },
        "required": ["haslo"]
    }
}

GET_PAGE_FUNCTION_DECL = {
    "name": "pobierzStrone",
    "description": "Pobiera surowy HTML strony o podanym URL.",
    "parameters": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"]
    }
}

TOOLS = [{
    "functionDeclarations": [
        DATE_TIME_FUNCTION_DECL,
        BTC_PRICE_FUNCTION_DECL,
        FIND_SITES_FUNCTION_DECL,
        GET_PAGE_FUNCTION_DECL,
    ]
}]

FUNCTION_MAP = {
    "pobierzDateCzas": lambda args: pobierzDateCzas(),
    "pobierzCeneBitcoin": lambda args: pobierzCeneBitcoin(args.get("waluta", "usd")),
    "znajdzStony": lambda args: znajdzStony(args.get("haslo", ""), args.get("limit", 5)),
    "pobierzStrone": lambda args: pobierzStrone(args.get("url", "")),
}


# =================== Internal Helpers ===================

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_log(role: str, content: str, meta: Optional[dict] = None):
    entry = {"ts": now_iso(), "role": role, "content": content}
    if meta:
        entry.update(meta)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def print_info(msg: str) -> None:
    print(f"\033[90m{msg}\033[0m")


def extract_function_call(data: dict) -> Optional[dict]:
    try:
        for p in data["candidates"][0]["content"].get("parts", []):
            if "functionCall" in p:
                return p["functionCall"]
    except Exception:
        pass
    return None


def extract_text(data: dict) -> str:
    try:
        parts = data["candidates"][0]["content"].get("parts", [])
        texts = [p.get("text") for p in parts if "text" in p]
        return "\n".join(t.strip() for t in texts if t.strip()) or "[Brak tekstu]"
    except Exception:
        return "[blad parsowania odpowiedzi API]"


# =================== Main Function Calling Loop ===================

def pytaj_Gemini_FC(prompt: str, history=None, system_prompt=None):
    history = history or []
    system_prompt = system_prompt or SYSTEM_PROMPT

    contents = []
    contents.append({"role": "user", "parts": [{"text": system_prompt}]})

    for msg in history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    contents.append({"role": "user", "parts": [{"text": prompt}]})

    payload = {"contents": contents, "generationConfig": GEN_CFG, "tools": TOOLS}

    resp = requests.post(API_URL, json=payload, timeout=120)
    data = resp.json()
    tool_call = extract_function_call(data)

    append_log("user", prompt)

    if not tool_call:
        text = extract_text(data)
        append_log("assistant", text)
        return text

    fname = tool_call["name"]
    fargs = tool_call.get("args", {})

    try:
        tool_result = FUNCTION_MAP[fname](fargs)
    except Exception as ex:
        tool_result = {"error": str(ex)}

    append_log("tool", f"{fname}({fargs}) -> {tool_result}")

    contents.append({
        "role": "user",
        "parts": [{
            "functionResponse": {
                "name": fname,
                "response": {"result": tool_result}
            }
        }]
    })

    resp2 = requests.post(API_URL, json=payload | {"contents": contents}, timeout=120)
    data2 = resp2.json()
    final_text = extract_text(data2)

    append_log("assistant", final_text, {"used_tool": True, "tool": fname})

    return final_text


# =================== CLI ===================

if __name__ == "__main__":
    print_info(f"Log: {LOG_FILE}")
    print_info("Tryb: Function Calling aktywny")
    print_info("Wyjscie: exit / quit\n")

    append_log("system", SYSTEM_PROMPT)
    history = []

    while True:
        try:
            user_input = input("ty: ")
        except (EOFError, KeyboardInterrupt):
            print("\nKoniec.")
            break

        if user_input.lower() in ["exit", "quit", "wyjscie", "q"]:
            break

        answer = pytaj_Gemini_FC(user_input, history)
        print("Gemini:", answer)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})

    print("Zapisano rozmowę:", LOG_FILE)
