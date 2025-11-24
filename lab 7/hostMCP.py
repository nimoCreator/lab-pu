"""
hostMCP.py

Aplikacja – host MCP dla modelu zdalnego Gemini.
 - prowadzi prosty chat w terminalu,
 - loguje pytania i odpowiedzi do pliku log.txt,
 - laczy sie jako klient MCP (HTTP / SSE) z serwerem MCP z zadania 2,
 - udostepnia narzedzia MCP modelowi Gemini poprzez mechanizm function calling.

Wymagane pakiety:
    pip install "mcp[cli]" google-genai python-dotenv

Wymagane zmienne srodowiskowe:
    GEMINI_API_KEY  - klucz API Gemini
    MCP_SERVER_URL  - adres serwera MCP (np. http://localhost:8000/sse)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

from mcp import ClientSession, types
from mcp.client.sse import sse_client 
from mcp.shared.context import RequestContext

from google import genai

LOG_FILE = "log.txt"
GEMINI_MODEL = "gemini-2.0-flash"  # mozesz zmienic na inny wspierajacy function calling


# =====================================================================
# Pomocnicze logowanie do pliku log.txt
# =====================================================================

def append_to_log(role: str, text: str) -> None:
    """Dopisuje linijke do log.txt w formacie:
       [YYYY-MM-DD HH:MM:SS] ROLE: tekst
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {role.upper()}: {text}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        # Przy logowaniu nie chcemy zabijac aplikacji
        print(f"(WARN) Nie udalo sie zapisac do log.txt: {e}", file=sys.stderr)


# =====================================================================
# Handler integrujacy Gemini z MCP (HTTP SSE)
# =====================================================================

class GeminiMCPHandler:
    """
    Odpowiada za:
    - polaczenie z Gemini,
    - pobranie listy narzedzi MCP i zamiane ich na deklaracje funkcji dla Gemini,
    - wykonywanie wywolanych przez model funkcji (czyli narzedzi MCP),
    - skladanie finalnej odpowiedzi dla uzytkownika.
    """

    def __init__(self, client_session: ClientSession, gemini_client: genai.Client):
        self.client_session = client_session
        self.gemini_client = gemini_client

    # -------------------------- MCP -> Gemini tools -------------------

    async def _get_tools_for_gemini(self) -> List[Dict[str, Any]]:
        """
        Pobiera liste narzedzi MCP i konwertuje je na format tools
        akceptowany przez Gemini (functionDeclarations).
        Dokumentacja: https://ai.google.dev/gemini-api/docs/function-calling
        """
        tools_resp = await self.client_session.list_tools()

        function_declarations = []
        for tool in tools_resp.tools:
            # MCP udostepnia inputSchema dla narzedzia – jest kompatybilne z OpenAPI/JSON Schema
            params_schema = getattr(
                tool,
                "inputSchema",
                {"type": "object", "properties": {}}
            )

            function_declarations.append(
                {
                    "name": tool.name,
                    "description": tool.description or "No description",
                    "parameters": params_schema,
                }
            )

        # Gemini spodziewa sie listy narzedzi, gdzie kazdy element ma pole functionDeclarations
        tools_for_gemini = [
            {
                "functionDeclarations": function_declarations
            }
        ]
        return tools_for_gemini

    async def _execute_mcp_tool(self, tool_call: Any) -> Dict[str, Any]:
        """
        Wykonuje jedno wywolanie narzedzia MCP w odpowiedzi na zlecenie modelu
        (functionCall z odpowiedzi Gemini).

        Zwraca:
          {
            "log": "[Used tool_name(args)]",
            "function_response_part": {...}  # czesc konwersacji dla Gemini
          }
        """
        tool_name = tool_call.name
        args = dict(tool_call.args) if tool_call.args else {}

        try:
            # Wywolanie narzedzia po stronie MCP
            result = await self.client_session.call_tool(tool_name, args)
            # Zakladamy pojedynczy content tekstowy
            content_text = ""
            if result.content:
                # MCP typowo zwraca liste content (TextContent, JSONContent itp.)
                first = result.content[0]
                # dla prostoty probujemy .text, jesli istnieje:
                content_text = getattr(first, "text", str(first))

            log_msg = f"[Used {tool_name}({json.dumps(args)})]"
            # Czesciowa odpowiedz funkcji (dla Gemini)
            function_response_part = {
                "functionResponse": {
                    "name": tool_name,
                    "response": {
                        "result": content_text
                    }
                }
            }

        except Exception as e:
            content_text = f"Error calling tool {tool_name}: {e}"
            log_msg = f"[{content_text}]"
            function_response_part = {
                "functionResponse": {
                    "name": tool_name,
                    "response": {
                        "result": content_text
                    }
                }
            }

        return {
            "log": log_msg,
            "function_response_part": function_response_part,
        }

    # -------------------------- glowne przetwarzanie -------------------

    async def process_query(self, query: str) -> str:
        """
        Przetwarza zapytanie uzytkownika:

        1) wysyla do Gemini tresc pytania + deklaracje funkcji (narzedzi MCP),
        2) sprawdza, czy model chce wywolac jakies funkcje (functionCall),
        3) jesli tak – wywoluje narzedzia MCP, buduje functionResponse,
        4) wysyla ponownie do Gemini wynik narzedzi + prosbe o finalna odpowiedz.
        """
        # 1. Przygotowanie narzedzi dla Gemini (functionDeclarations)
        tools = await self._get_tools_for_gemini()

        # 2. Pierwsze wywolanie modelu – model decyduje, czy uzyc funkcji
        #    Uzywamy klienta google-genai (Gemini API)
        #    Dokumentacja: https://googleapis.github.io/python-genai/
        def _call_gemini_once(contents: List[dict], tools: List[dict] | None = None):
            return self.gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                tools=tools or [],
            )

        # Konwersacja w formacie Gemini:
        # pojedyncza wiadomosc usera
        conversation: List[dict] = [
            {
                "role": "user",
                "parts": [{"text": query}],
            }
        ]

        initial_response = await asyncio.to_thread(
            _call_gemini_once,
            conversation,
            tools,
        )

        # Bierzemy pierwszego kandydata
        candidate = initial_response.candidates[0]
        parts = candidate.content.parts

        result_parts: List[str] = []
        function_calls: List[Any] = []

        # Przetwarzamy wszystkie parts – moga zawierac tekst i/lub functionCall
        for part in parts:
            if getattr(part, "text", None):
                result_parts.append(part.text)
            if getattr(part, "function_call", None):
                function_calls.append(part.function_call)

        # Jesli nie ma wywolan funkcji – zwracamy sama odpowiedz modelu
        if not function_calls:
            assistant_text = "\n".join(result_parts).strip()
            if not assistant_text:
                assistant_text = "(Brak odpowiedzi od modelu)"
            return assistant_text

        # 3. Jesli sa funkcje do wywolania – uruchamiamy narzedzia MCP
        tool_logs: List[str] = []
        function_response_parts: List[dict] = []

        for fc in function_calls:
            tool_result = await self._execute_mcp_tool(fc)
            tool_logs.append(tool_result["log"])
            function_response_parts.append(tool_result["function_response_part"])

        # Doklejamy functionResponse do konwersacji i robimy drugie wywolanie Gemini
        conversation.append(
            {
                "role": "model",  # model wygenerowal functionCall
                "parts": parts,
            }
        )
        conversation.append(
            {
                "role": "user",  # my "uzytkownik systemowy" przekazujemy wyniki funkcji
                "parts": function_response_parts,
            }
        )

        final_response = await asyncio.to_thread(
            _call_gemini_once,
            conversation,
            None,  # teraz bez tools – model ma juz wyniki funkcji
        )

        final_candidate = final_response.candidates[0]
        final_text_parts = []
        for p in final_candidate.content.parts:
            if getattr(p, "text", None):
                final_text_parts.append(p.text)

        final_text = "\n".join(result_parts + tool_logs + final_text_parts).strip()
        if not final_text:
            final_text = "(Brak finalnej odpowiedzi od modelu)"

        return final_text


# =====================================================================
# Prosty chat w terminalu z logowaniem do log.txt
# =====================================================================

async def run_chat(handler: GeminiMCPHandler) -> None:
    """
    Prosta petla chatowa:
      - pobiera pytanie z input(),
      - wysyla do handlera,
      - wypisuje i loguje odpowiedz.
    Komenda 'quit' konczy program.
    """
    print("=== MCP + Gemini chat (hostMCP) ===")
    print("Wpisz swoje pytanie, 'quit' aby zakonczyc.\n")

    while True:
        try:
            user = input("Ty: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nKoniec.")
            return

        if not user:
            continue
        if user.lower() == "quit":
            print("Koniec.")
            return

        append_to_log("user", user)

        try:
            answer = await handler.process_query(user)
        except Exception as e:
            answer = f"(Blad podczas przetwarzania zapytania: {e})"

        print(f"\nAsystent: {answer}\n")
        append_to_log("assistant", answer)


# =====================================================================
# Inicjalizacja: polaczenie z serwerem MCP (HTTP SSE) i Gemini
# =====================================================================

async def main() -> None:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("BLAD: Brak zmiennej srodowiskowej GEMINI_API_KEY.", file=sys.stderr)
        sys.exit(1)

    mcp_url = os.getenv("MCP_SERVER_URL", "").strip()
    if not mcp_url:
        print("BLAD: Brak zmiennej srodowiskowej MCP_SERVER_URL.", file=sys.stderr)
        print("Przyklad: MCP_SERVER_URL=http://localhost:8000/sse", file=sys.stderr)
        sys.exit(1)

    print(f"Łacze z MCP (HTTP SSE): {mcp_url}")
    print(f"Model Gemini: {GEMINI_MODEL}")

    # Inicjalizacja klienta Gemini
    gemini_client = genai.Client(api_key=api_key)

    # Polaczenie z serwerem MCP po HTTP (SSE)
    from pydantic import AnyUrl

    async with sse_client(AnyUrl(mcp_url)) as (read, write):
        async with ClientSession(read, write) as session:
            # inicjalizacja MCP
            await session.initialize()

            # dla debug – wypisz dostepne narzedzia
            tools_resp = await session.list_tools()
            tool_names = [t.name for t in tools_resp.tools]
            print("Dostepne narzedzia MCP:", ", ".join(tool_names) or "(brak)")

            handler = GeminiMCPHandler(session, gemini_client)
            await run_chat(handler)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrzerwano przez uzytkownika.")
