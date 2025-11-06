import time
import json
import pathlib
from datetime import datetime, timezone
from typing import Tuple
from llama_cpp import Llama

MODEL_PATH = "./models/Qwen3-8B-Q5_0.gguf"
CONTEXT_SIZE = 4096
THREADS = 12
GPU_LAYERS = 999

LOG_DIR = pathlib.Path("./logs_qwen")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"qwen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _append_qwen_log(entry: dict) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        f.flush()  # immediate write so you can tail the file

_llm = None  # singleton

def get_llm() -> Llama:
    global _llm
    if _llm is None:
        _llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=CONTEXT_SIZE,
            n_threads=THREADS,
            n_gpu_layers=GPU_LAYERS,
            logits_all=False,
            verbose=False,
        )
    return _llm

STOP = ["###", "\n###", "\n\n###", "### Pytanie:", "### System:"]

def pytaj_Qwen(
    prompt: str,
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 96
) -> Tuple[str, float]:
    """
    Pyta lokalny model Qwen (GGUF przez llama-cpp-python).
    Zwraca (odpowiedz, latency_s).
    """
    llm = get_llm()
    system = "Odpowiadaj krotko i rzeczowo po polsku."
    full_prompt = f"### System:\n{system}\n\n### Pytanie:\n{prompt}\n\n### Odpowiedz:\n"

    t0 = time.perf_counter()
    out = llm.create_completion(
        prompt=full_prompt,
        temperature=temperature,
        top_p=top_p,
        top_k=40,
        max_tokens=max_tokens,
        stop=STOP,
        repeat_penalty=1.2,
    )
    latency = round(time.perf_counter() - t0, 3)
    text = (out["choices"][0]["text"] or "").strip()

    for s in STOP:
        if s in text:
            text = text.split(s, 1)[0].strip()

    # log this call
    _append_qwen_log({
        "ts": _now_iso(),
        "type": "qwen_answer",
        "prompt": prompt,
        "answer": text,
        "latency_s": latency
    })

    return text, latency


if __name__ == "__main__":
    ans, t = pytaj_Qwen("Ile jest kart w standardowej talii?")
    print(f"Test 1: {ans}  (czas: {t}s)")
    ans, t = pytaj_Qwen("Podaj 3 najwieksze miasta w Polsce.")
    print(f"Test 2: {ans}  (czas: {t}s)")
    print(f"Qwen log: {LOG_FILE}")
