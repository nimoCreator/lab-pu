import asyncio
import json
from datetime import datetime

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from google import genai
from google.genai import types as genai_types

LOG_FILE = "log.txt"
MODEL_NAME = "gemini-2.0-flash"
API_KEY = "AIzaSyAaHR5vCGU_cCLvxfKR2p4ppa4cuwbzeJI"

MCP_SERVER_URL = "http://127.0.0.1:8000/mcp"


def log(role: str, text: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}: {text}\n")


class GeminiMCPHandler:
    def __init__(self, session: ClientSession, gemini_client: genai.Client):
        self.session = session
        self.gemini_client = gemini_client

    async def _build_tool_config(self) -> genai_types.GenerateContentConfig:
        """
        Pobiera liste MCP tools i zamienia na FunctionDeclaration + Tool
        dla Google GenAI.
        """
        tools = await self.session.list_tools()

        function_decls: list[genai_types.FunctionDeclaration] = []

        for t in tools.tools:
            schema = getattr(t, "inputSchema", None) or {
                "type": "object",
                "properties": {},
            }

            fn = genai_types.FunctionDeclaration(
                name=t.name,
                description=t.description or "",
                parameters_json_schema=schema,
            )
            function_decls.append(fn)

        tool = genai_types.Tool(function_declarations=function_decls)

        # automatic_function_calling.disable=True => model ZWRACA function_calls,
        # ale ich nie wykonuje – my je obslugujemy recznie.
        config = genai_types.GenerateContentConfig(
            tools=[tool],
            automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        )
        return config

    async def _call_mcp_tool(self, tool_call: genai_types.FunctionCall) -> dict:
        """
        Wywoluje narzedzie MCP na podstawie FunctionCall.
        Dziala zarowno z wersjami SDK, gdzie jest .function_call.args,
        jak i tam, gdzie args sa bezposrednio na obiekcie.
        """
        name = tool_call.name

        # Proba nowego API (function_call.args) – jak w dokumentacji
        inner = getattr(tool_call, "function_call", None)
        raw_args = None
        if inner is not None:
            raw_args = getattr(inner, "args", None)

        # Fallback dla wersji, gdzie args sa bezposrednio
        if raw_args is None:
            raw_args = getattr(tool_call, "args", {}) or {}

        # Na wszelki wypadek zamieniamy na dict
        try:
            args = dict(raw_args)
        except TypeError:
            # jakby to bylo juz dict/Mapping pydanticowe, to tez przejdzie
            args = raw_args

        try:
            result = await self.session.call_tool(name, args)
            content = result.content[0] if result.content else None
            result_text = getattr(content, "text", str(content))
        except Exception as e:
            result_text = f"Error calling tool: {e}"

        log("tool", f"{name}({json.dumps(args)}) -> {result_text}")

        return {"result": result_text}

    async def process(self, user_text: str) -> str:
        tool_config = await self._build_tool_config()

        def _gemini(contents, config: genai_types.GenerateContentConfig | None):
            return self.gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )

        # === 1. Pierwsze wywolanie – model decyduje, czy potrzebuje funkcji ===
        initial = await asyncio.to_thread(
            _gemini,
            user_text,          # string -> SDK zrobi z tego UserContent
            tool_config,
        )

        # Jezeli model nie chce funkcji, mamy zwykly tekst
        function_calls = list(initial.function_calls or [])
        if not function_calls:
            return initial.text or "(empty response)"

        # === 2. Wywolujemy MCP tools ===
        tool_results: list[tuple[genai_types.FunctionCall, dict]] = []
        for call in function_calls:
            result_obj = await self._call_mcp_tool(call)
            tool_results.append((call, result_obj))

        # === 3. Drugi przebieg: user prompt + function_call + function_response ===

        # a) oryginalny prompt usera
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=user_text)],
        )

        # b) to, co model wygenerowal w pierwszej odpowiedzi (zawiera function_calls)
        function_call_content = initial.candidates[0].content

        # c) odpowiedzi narzedzi jako role="tool"
        response_parts: list[genai_types.Part] = []
        for call, result_obj in tool_results:
            part = genai_types.Part.from_function_response(
                name=call.name,
                response=result_obj,
            )
            response_parts.append(part)

        function_response_content = genai_types.Content(
            role="tool",
            parts=response_parts,
        )

        final = await asyncio.to_thread(
            _gemini,
            [user_content, function_call_content, function_response_content],
            tool_config,
        )

        return final.text or "(empty response)"


async def chat(handler: GeminiMCPHandler):
    print("\n🚀 Gemini MCP Chat Ready!")
    print("Type 'quit' to exit.\n")

    while True:
        user = input("You: ").strip()
        if user.lower() == "quit":
            print("👋 Bye!")
            return

        log("user", user)
        reply = await handler.process(user)
        print("\nAssistant:", reply, "\n")
        log("assistant", reply)


async def main():
    # Klient Gemini
    gemini = genai.Client(api_key=API_KEY)
    mcp_url = MCP_SERVER_URL

    print("🔌 Connecting to MCP:", mcp_url)

    # Klient MCP po streamable-http – dopasowany do FastMCP
    async with streamablehttp_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("🛠 Tools:", [t.name for t in tools.tools])

            handler = GeminiMCPHandler(session, gemini)
            await chat(handler)


if __name__ == "__main__":
    asyncio.run(main())
