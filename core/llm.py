from ollama import chat

MODEL = "qwen3:8b"

SYSTEM_PROMPT = """
You are JARVIS.

You are an intelligent AI assistant inspired by Iron Man's JARVIS.

Be concise, professional, and helpful.

Never reveal your underlying model unless explicitly asked.
"""

conversation = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT,
    }
]


def ask_llm(user_message: str) -> str:
    conversation.append(
        {
            "role": "user",
            "content": user_message,
        }
    )

    response = chat(
        model=MODEL,
        messages=conversation,
    )

    assistant_message = response.message.content

    conversation.append(
        {
            "role": "assistant",
            "content": assistant_message,
        }
    )

    return assistant_message
