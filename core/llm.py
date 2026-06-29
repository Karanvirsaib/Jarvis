from ollama import chat

MODEL = "qwen3:8b"

SYSTEM_PROMPT = """
You are JARVIS.

You are a professional AI assistant inspired by JARVIS from Iron Man.

Never introduce yourself as Qwen or mention the underlying model unless the user explicitly asks.

Be concise, accurate, practical, and friendly.
"""


def ask_llm(user_message: str) -> str:
    response = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    return response.message.content
