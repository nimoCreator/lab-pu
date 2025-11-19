import json
import time
import pathlib
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

API_KEY = "AIzaSyBWoUQqQTEvx8gI7hD34Enl6AgV5WELe3g" 
MODEL_NAME = "gemini-2.5-flash"
API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
)

LOG_DIR = pathlib.Path(".")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "logFC_z2.txt"

SYSTEM_PROMPT = (
    "Jestes pomocnym asystentem. "
    "Masz dostep do funkcji, ktore pozwalaja pobrac aktualna date i czas, oraz wyszukujacej stron internetowych i pobierajacej ich zawartosc."
    "jezeli uzyjesz funkcji, ładnie opisz w odpowiedzi, którą z niej uzyskałeś."
    "jezeli uzytkownik zadaje pytanie, mozesz najpierw wyszukac strony zwiazane z tematem, a nastepnie pobrac ich zawartosc i na tej podstawie udzielic odpowiedzi."
)
GEN_CFG = {"temperature": 0.7, "topP": 0.9}

def pobierzDateCzas() -> str:
    """
    Używa biblioteki datetime do pobrania aktualnej daty i czasu.
    
    :returns: Data i czas w formacie 'YYYY-MM-DD HH:MM:SS'
    """
    teraz = datetime.now()
    return teraz.strftime("%Y-%m-%d %H:%M:%S")

def pobierzCeneBitcoin(waluta: str = "usd") -> float:
    """
    Używa API CoinGecko do pobrania aktualnej ceny Bitcoina w podanej walucie.

    :param waluta: Kod waluty, np. 'usd', 'eur', 'pln'. Domyślnie 'usd'.
    :returns: Cena Bitcoina w podanej walucie.
    """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={waluta}"
    resp = requests.get(url, timeout=10)
    dane = resp.json()
    return dane["bitcoin"][waluta]

def znajdzStony(haslo: str, limit: int = 5) -> list[dict]:
    """
    Korzysta z darmowego API DuckDuckGo (Instant Answer API),
    aby znalezc strony pasujace do podanego hasla.
    Zwraca liste obiektow: {"url": ..., "opis": ...},
    gdzie url jest MOZLIWIE docelowym adresem (po przekierowaniu).
    """
    base_url = "https://api.duckduckgo.com/"
    params = {
        "q": haslo,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
        "skip_disambig": 1,
    }
    resp = requests.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results: list[dict] = []

    def resolve_duckduckgo_url(url: str) -> str:
        """
        Jesli url wskazuje na duckduckgo.com/<cos>, probujemy wykonac GET
        i zwrocic finalny adres po przekierowaniach (np. Wikipedia).
        Jesli cos pojdzie nie tak – zwracamy oryginalny url.
        """
        try:
            parsed = urlparse(url)
            if "duckduckgo.com" not in parsed.netloc:
                return url  # to juz jest zewnetrzna strona

            r = requests.get(url, timeout=10, allow_redirects=True)
            return r.url or url
        except Exception:
            return url

    def add_item(item: dict):
        nonlocal results
        if "FirstURL" in item and "Text" in item:
            raw_url = item["FirstURL"]
            final_url = resolve_duckduckgo_url(raw_url)
            results.append({
                "url": final_url,
                "opis": item["Text"],
            })

    # 1) Bezposrednie wyniki
    for item in data.get("Results", []):
        add_item(item)
        if len(results) >= limit:
            return results

    # 2) RelatedTopics (zagniezdzone)
    def extract_topics(topics):
        for item in topics:
            if "FirstURL" in item and "Text" in item:
                add_item(item)
                if len(results) >= limit:
                    return
            if "Topics" in item:
                extract_topics(item["Topics"])
                if len(results) >= limit:
                    return

    extract_topics(data.get("RelatedTopics", []))
    return results



def pobierzStrone(url: str) -> str:
    """
    Pobiera zawartosc HTML strony o podanym URL.
    """
    resp = requests.get(url, timeout=10)
    return resp.text


DATE_TIME_FUNCTION_DECL = {
    "name": "pobierzDateCzas",
    "description": "Zwraca aktualna date i czas jako tekst w formacie 'YYYY-MM-DD HH:MM:SS'.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

BTC_PRICE_FUNCTION_DECL = {
    "name": "pobierzCeneBitcoin",
    "description": "Zwraca aktualna cene Bitcoina w podanej walucie.",
    "parameters": {
        "type": "object",
        "properties": {
            "waluta": {
                "type": "string",
                "description": "Kod waluty, np. 'usd', 'eur', 'pln'."
            }
        },
        "required": []
    }
}

FIND_SITES_FUNCTION_DECL = {
    "name": "znajdzStony",
    "description": (
        "Dla podanego hasla wyszukuje w DuckDuckGo pasujace strony. "
        "Zwraca liste obiektow z polami 'url' i 'opis'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "haslo": {
                "type": "string",
                "description": "Haslo / fraza do wyszukania."
            },
            "limit": {
                "type": "integer",
                "description": "Maksymalna liczba wynikow (domyslnie 5)."
            }
        },
        "required": ["haslo"]
    }
}

GET_PAGE_FUNCTION_DECL = {
    "name": "pobierzStrone",
    "description": "Pobiera zawartosc HTML strony o podanym URL.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Pelny URL strony, np. 'https://example.com/'."
            }
        },
        "required": ["url"]
    }
}

TOOLS = [
    {
        "functionDeclarations": [
            DATE_TIME_FUNCTION_DECL,
            BTC_PRICE_FUNCTION_DECL,
            FIND_SITES_FUNCTION_DECL,
            GET_PAGE_FUNCTION_DECL,
        ]
    }
]

FUNCTION_MAP: dict[str, callable] = {
    "pobierzDateCzas": lambda args: pobierzDateCzas(),
    "pobierzCeneBitcoin": lambda args: pobierzCeneBitcoin(args.get("waluta", "usd")),
    "znajdzStony": lambda args: znajdzStony(args.get("haslo", ""), args.get("limit", 5)),
    "pobierzStrone": lambda args: pobierzStrone(args.get("url", "")),
}



def now_iso() -> str:
    """
    Zwraca aktualny czas w formacie ISO 8601 z dokładnością do sekund.

    :returns: Aktualny czas jako string ISO 8601
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def append_log(role: str, content: str, meta: Optional[dict] = None) -> None:
    """
    Dopisuje wpis do pliku logu.

    :param role: Rola wpisu (np. 'user', 'assistant', 'tool')
    :param content: Treść wpisu
    :param meta: Dodatkowe metadane jako słownik
    """
    entry: Dict[str, Any] = {"ts": now_iso(), "role": role, "content": content}
    if meta:
        entry.update(meta)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()

def print_info(msg: str) -> None:
    """
    Wypisuje informacyjny komunikat na konsolę w szarym kolorze.

    :param msg: Treść komunikatu
    """
    print(f"\033[90m{msg}\033[0m")



def extract_function_call(data: dict) -> Optional[dict]:
    """
    Standardowe wyciagniecie wywolania funkcji z odpowiedzi modelu.

    :param data: Odpowiedz modelu jako slownik

    :returns: Slownik z wywolaniem funkcji lub None, jesli brak
    """
    try:
        candidate = data["candidates"][0]
        parts = candidate["content"].get("parts", [])
        for p in parts:
            if "functionCall" in p:
                return p["functionCall"]
    except Exception:
        return None
    return None


def extract_text(data: dict) -> str:
    """
    Wyciaga tekst z odpowiedzi modelu.
    Przechodzi po wszystkich parts i sklada wszystkie fragmenty 'text'.
    """
    try:
        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])
        texts = [p["text"] for p in parts if isinstance(p, dict) and "text" in p]

        if texts:
            joined = "\n".join(t.strip() for t in texts if t.strip())
            return joined if joined else "[pusta odpowiedz tekstowa z API]"
        else:
            return "[brak pola 'text' w parts odpowiedzi API]"
    except Exception as e:
        return f"[blad parsowania odpowiedzi API: {e}]"



def pytaj_Gemini_FC(
    prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Wysyła zapytanie do modelu Gemini z funkcjami (function calling).
    
    :param prompt: Tekst zapytania od uzytkownika
    :param history: Historia rozmowy jako lista slownikow z kluczami 'role' i 'content'
    :param system_prompt: Opcjonalny prompt systemowy

    :returns: Odpowiedz modelu jako tekst
    """
    if not API_KEY:
        raise RuntimeError("Brak API_KEY. Ustaw w kodzie zmiennej API_KEY.")

    system_prompt = system_prompt or SYSTEM_PROMPT
    history = history or []

    contents: List[Dict[str, Any]] = []

    if system_prompt:
        contents.append({
            "role": "user",
            "parts": [{"text": system_prompt}]
        })

    for msg in history:
        role = msg["role"]
        if role == "system":
            role = "user"
        elif role == "assistant":
            role = "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    payload = {
        "contents": contents,
        "generationConfig": GEN_CFG,
        "tools": TOOLS,
    }

    t0 = time.perf_counter()
    resp = requests.post(API_URL, json=payload, timeout=120)
    dt = round(time.perf_counter() - t0, 3)

    if not resp.ok:
        append_log("assistant", f"HTTP {resp.status_code}: {resp.text}", {"error": True})
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    tool_call = extract_function_call(data)

    append_log("user", prompt)

    if not tool_call:
        text = extract_text(data)
        append_log("assistant", text, {"latency_s": dt, "used_tool": False})
        return text

    fname = tool_call.get("name")
    fargs = tool_call.get("args", {}) or {}

    tool_result: Any = None

    try:
        if fname in FUNCTION_MAP:
            tool_result = FUNCTION_MAP[fname](fargs)
        else:
            tool_result = {"error": f"Nieznana funkcja: {fname}"}
    except Exception as ex:
        tool_result = {"error": f"Wyjatek podczas wykonywania funkcji: {ex}"}


    append_log(
        "tool",
        f"call {fname}({fargs}) -> {tool_result}",
        {"tool_name": fname, "tool_args": fargs}
    )
    
    try:
        model_content = data["candidates"][0]["content"]
    except Exception:
        model_content = {
            "role": "model",
            "parts": [{"functionCall": tool_call}]
        }

    contents2 = contents[:]  
    contents2.append(model_content)
    contents2.append({
        "role": "user",
        "parts": [{
            "functionResponse": {
                "name": fname,
                "response": {"result": tool_result}
            }
        }]
    })

    payload2 = {
        "contents": contents2,
        "generationConfig": GEN_CFG,
        "tools": TOOLS,
    }

    t1 = time.perf_counter()
    resp2 = requests.post(API_URL, json=payload2, timeout=120)
    dt2 = round(time.perf_counter() - t1, 3)

    if not resp2.ok:
        # lagodna obsluga bledu modelu (np. 503 "model overloaded")
        msg = (
            f"Model zwrocil blad HTTP {resp2.status_code} podczas drugiego kroku "
            f"(np. przeciazenie). Mimo to funkcja {fname} zostala poprawnie "
            f"wykonana po naszej stronie. Wynik funkcji: {tool_result!r}."
        )
        append_log(
            "assistant",
            msg,
            {"error": True, "stage": "after_tool", "tool_name": fname}
        )
        return msg


    data2 = resp2.json()
    final_text = extract_text(data2)

    if final_text.startswith("[blad parsowania") or final_text.startswith("[brak pola"):
        append_log(
            "assistant_raw",
            json.dumps(data2, ensure_ascii=False),
            {"stage": "raw_after_tool"}
        )

        if fname == "znajdzStony":
            if tool_result == []:
                final_text = (
                    "Uzylem funkcji wyszukiwania stron (znajdzStony) z haslem "
                    f"{fargs.get('haslo')!r}, ale nie znalazlem zadnych pasujacych wynikow. "
                    "Na tej podstawie nie moge potwierdzic zadnych nowych zapowiedzi."
                )
            else:
                final_text = (
                    "Uzylem funkcji wyszukiwania stron (znajdzStony). "
                    "Znalazlem nastepujace strony:\n"
                    + "\n".join(f"- {item['url']}: {item['opis']}" for item in tool_result[:5])
                )
        elif fname == "pobierzDateCzas":
            final_text = (
                "Uzylem funkcji pobierzDateCzas i otrzymalem aktualna date i czas: "
                f"{tool_result}."
            )
        elif fname == "pobierzCeneBitcoin":
            final_text = (
                "Uzylem funkcji pobierzCeneBitcoin. "
                f"Aktualna cena Bitcoina to ok. {tool_result} {fargs.get('waluta','usd').upper()}."
            )
        elif fname == "pobierzStrone":
            final_text = (
                "Uzylem funkcji pobierzStrone i pobralem zawartosc HTML strony.\n\n"
                "Ze wzgledu na dlugosc kodu nie wypisuje calego HTML, ale moge "
                "na jego podstawie odpowiedziec na bardziej konkretne pytania."
            )
        else:
            final_text = (
                f"Uzylem funkcji {fname} z argumentami {fargs} i otrzymalem wynik: {tool_result!r}."
            )

    append_log(
        "assistant",
        final_text,
        {
            "latency_s_first": dt,
            "latency_s_second": dt2,
            "used_tool": True,
            "tool_name": fname,
        },
    )

    return final_text


# ======================= MAIN =======================

if __name__ == "__main__":
    print_info(f"Log do pliku (function calling): {LOG_FILE}")
    print_info("Tryb: SYSTEM Z FUNCTION CALLINGIEM (czas + cena BTC).")
    print_info("Komendy wyjscia: exit / quit / wyjscie\n")

    append_log("system", SYSTEM_PROMPT)

    history: List[Dict[str, str]] = []

    while True:
        try:
            user_input = input("ty: ")
        except (EOFError, KeyboardInterrupt):
            print_info("\nPrzerwano przez uzytkownika.")
            break

        if user_input.strip().lower() in [
            "exit", "quit", "wyjscie", "e", "q", "w",
            "/exit", "/quit", "/wyjscie"
        ]:
            break

        answer = pytaj_Gemini_FC(user_input, history=history)
        print("Gemini:", answer)

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": answer})

    print_info(f"Koniec. Rozmowa zapisana w {LOG_FILE}")
