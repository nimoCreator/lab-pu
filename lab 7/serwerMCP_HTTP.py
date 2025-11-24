# serwerMCP_HTTP.py
"""
Serwer MCP korzystajacy z FastMCP i transportu HTTP SSE.

Udostepnia trzy narzedzia:
1) get_current_datetime() – bezparametrowe, zwraca aktualna date/czas
   w formacie "YYYY-MM-DD HH:MM:SS"
2) get_today_wordle_answer() – pobiera dzisiejsza odpowiedz Wordle z API NYT
3) generate_sudoku() – generuje losowe sudoku (plansza + rozwiazanie)

Transport: HTTP (SSE) – np. http://127.0.0.1:8000
"""

from fastmcp import FastMCP
from typing import TypedDict, List
import logging
import sys
import random
import datetime
import requests

# Logowanie na stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

# Tworzymy serwer MCP
mcp = FastMCP("SerwerMCP_HTTP_Demo")


# ============================================================
# Narzedzie 1: aktualna data i czas
# ============================================================

@mcp.tool()
def get_current_datetime() -> str:
    """
    Zwraca aktualna date i czas w formacie 'YYYY-MM-DD HH:MM:SS'.
    """
    now = datetime.datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Zwracam aktualna date/czas: %s", formatted)
    return formatted


# ============================================================
# Narzedzie 2: dzisiejsza odpowiedz Wordle
# ============================================================

class WordleResult(TypedDict):
    date: str
    solution: str


@mcp.tool()
def get_today_wordle_answer() -> WordleResult:
    """
    Pobiera dzisiejsza odpowiedz Wordle z API NYT.
    API: https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json
    """
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    url = f"https://www.nytimes.com/svc/wordle/v2/{date_str}.json"

    logging.info("Pobieram Wordle z URL: %s", url)

    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.error("Blad API Wordle: %s", e)
        raise RuntimeError(f"Nie udalo sie pobrac odpowiedzi Wordle: {e}")

    solution = data.get("solution")
    if not solution:
        raise RuntimeError("API Wordle nie zwrocilo pola 'solution'.")

    logging.info("Wordle %s: %s", date_str, solution)

    return {
        "date": date_str,
        "solution": solution,
    }


# ============================================================
# Narzedzie 3: generowanie sudoku
# ============================================================

class SudokuResult(TypedDict):
    puzzle: List[List[int]]
    solution: List[List[int]]


def _is_safe(board: List[List[int]], row: int, col: int, num: int) -> bool:
    if any(board[row][c] == num for c in range(9)):
        return False
    if any(board[r][col] == num for r in range(9)):
        return False
    sr, sc = (row // 3) * 3, (col // 3) * 3
    for r in range(sr, sr + 3):
        for c in range(sc, sc + 3):
            if board[r][c] == num:
                return False
    return True


def _find_empty(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def _generate_full_board(board) -> bool:
    empty = _find_empty(board)
    if empty is None:
        return True
    row, col = empty
    nums = list(range(1, 10))
    random.shuffle(nums)
    for num in nums:
        if _is_safe(board, row, col, num):
            board[row][col] = num
            if _generate_full_board(board):
                return True
            board[row][col] = 0
    return False


def _make_puzzle(solution, min_removed=40, max_removed=55):
    puzzle = [row[:] for row in solution]
    removals = random.randint(min_removed, max_removed)
    count = 0
    while count < removals:
        r = random.randint(0, 8)
        c = random.randint(0, 8)
        if puzzle[r][c] != 0:
            puzzle[r][c] = 0
            count += 1
    return puzzle


@mcp.tool()
def generate_sudoku() -> SudokuResult:
    """
    Generuje sudoku: puzzle + solution.
    """
    board = [[0] * 9 for _ in range(9)]
    if not _generate_full_board(board):
        raise RuntimeError("Nie udalo sie wygenerowac sudoku.")
    solution = [row[:] for row in board]
    puzzle = _make_puzzle(solution)
    return {
        "puzzle": puzzle,
        "solution": solution,
    }


# ============================================================
# Start MCP HTTP server (SSE)
# ============================================================

if __name__ == "__main__":
    # Uruchamiamy serwer MCP po HTTP (SSE) na porcie 8000.
    # Domyslny host: 127.0.0.1
    #
    # Po starcie bedzie dostepny np. pod:
    #   http://127.0.0.1:8000/
    #
    # Klient MCP (LM Studio / Chatbox) laczy sie przez HTTP SSE.
    mcp.run_http(host="127.0.0.1", port=8000)
