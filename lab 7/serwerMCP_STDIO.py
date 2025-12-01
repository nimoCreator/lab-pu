from fastmcp import FastMCP
from typing import TypedDict, List
import logging
import sys
import random
import datetime
import requests

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)

mcp = FastMCP("MCP_Server_STDIO")


# ================================= Current Date/Time =================================

@mcp.tool()
def get_current_datetime() -> str:
    """
    Returns the current date and time formatted as 'YYYY-MM-DD HH:MM:SS'.
    """
    now = datetime.datetime.now()
    formatted = now.strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Returning current datetime: %s", formatted)
    return formatted


# ================================= Wordle API =================================

class WordleResult(TypedDict):
    date: str
    solution: str


@mcp.tool()
def get_today_wordle_answer() -> WordleResult:
    """
    Fetches today's Wordle solution from NYT public API.
    API: https://www.nytimes.com/svc/wordle/v2/YYYY-MM-DD.json
    """
    today = datetime.date.today()
    date_str = today.strftime("%Y-%m-%d")
    url = f"https://www.nytimes.com/svc/wordle/v2/{date_str}.json"

    logging.info("Fetching Wordle from URL: %s", url)

    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logging.error("Wordle API error: %s", e)
        raise RuntimeError(f"Failed to fetch Wordle: {e}")

    solution = data.get("solution")
    if not solution:
        raise RuntimeError("API did not return 'solution' field.")

    logging.info("Wordle %s: %s", date_str, solution)

    return {
        "date": date_str,
        "solution": solution,
    }


# ================================= Sudoku Generator =================================

class SudokuResult(TypedDict):
    puzzle: List[List[int]]
    solution: List[List[int]]


def _is_safe(board: List[List[int]], row: int, col: int, num: int) -> bool:
    """Checks if num can be safely placed at (row, col)."""
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
    """Finds the next empty cell (0)."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return r, c
    return None


def _generate_full_board(board) -> bool:
    """Recursively fills the board with a valid sudoku solution."""
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


def _make_puzzle(solution, removals: int):
    """
    Removes 'removals' number of cells from the solution to form the puzzle.
    """
    puzzle = [row[:] for row in solution]
    removals = max(0, min(81, removals))
    count = 0
    while count < removals:
        r = random.randint(0, 8)
        c = random.randint(0, 8)
        if puzzle[r][c] != 0:
            puzzle[r][c] = 0
            count += 1
    return puzzle


@mcp.tool()
def generate_sudoku(fill_percent: int = 50) -> SudokuResult:
    """
    Generates sudoku: puzzle + solution.

    Parameters:
    - fill_percent (int): 0–100, percentage of cells that remain filled in the puzzle.
        * 0  -> empty board
        * 100 -> fully filled board

    Values outside range [0, 100] will be capped.
    Ensures at least 1 and at most 80 filled cells remain for valid gameplay.
    """
    original = fill_percent
    fill_percent = max(0, min(100, int(fill_percent)))
    if fill_percent != original:
        logging.info(
            "fill_percent (%s) was capped to %s",
            original,
            fill_percent,
        )

    filled_cells = round(81 * (fill_percent / 100.0))
    filled_cells = max(1, min(80, filled_cells))
    removals = 81 - filled_cells

    logging.info(
        "Generating sudoku: fill_percent=%s => filled_cells=%s, removals=%s",
        fill_percent,
        filled_cells,
        removals,
    )

    board = [[0] * 9 for _ in range(9)]
    if not _generate_full_board(board):
        raise RuntimeError("Failed to generate sudoku solution.")
    solution = [row[:] for row in board]
    puzzle = _make_puzzle(solution, removals=removals)
    return {
        "puzzle": puzzle,
        "solution": solution,
    }


# ================================= MAIN =================================

if __name__ == "__main__":
    mcp.run()
