from llama_cpp import Llama

QWEN_MODEL_PATH = "P:\\lab-pu\\lab 5\\zadanie 2\\model\\Qwen3-4B-Instruct-2507-Q4_K_M.gguf"

TEST_QUESTIONS = [
    "Whats the newest headset released by Vallve",
    "Who is the current president of the United States?",
    "What is the acronym TUC stand for in context of Polish University Subject?",
]

def build_prompt(question: str) -> str:
    return (
        "You are a helpful assistant. Answer the question as precisely as possible.\n\n"
        f"Question: {question}\n"
        "Answer:"
    )

if __name__ == "__main__":
    llm = Llama(
        model_path=QWEN_MODEL_PATH,
        n_ctx=4096,
        n_threads=4,  
    )

    print("========================================\nModel loaded. Testing questions...\n========================================\n")

    with open("qwen_answers_log.txt", "w", encoding="utf-8") as log:
        for i, q in enumerate(TEST_QUESTIONS, start=1):
            prompt = build_prompt(q)
            print(f"Q{i}: {q}")
            output = llm(
                prompt,
                max_tokens=256,
                temperature=0.7,
                top_p=0.9,
            )
            answer = output["choices"][0]["text"].strip()
            print("A:", answer)
            print("-" * 60)

            log.write(f"Q{i}: {q}\n")
            log.write(f"A{i}: {answer}\n")
            log.write("-" * 60 + "\n\n")

    print("Gotowe. Sprawdz qwen_answers_log.txt i recznie wypisz luki do luki.txt.")
