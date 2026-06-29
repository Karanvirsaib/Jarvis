from ollama import chat
import json


def ask_llm(user_input, context=""):

    system_prompt = f"""
You are JARVIS.

Return ONLY valid JSON in this format:

{{
  "answer": "final response"
}}

Rules:
- No greetings
- No emojis
- No extra text
- Only JSON output
- If memory answers the question, use it
- If unknown, return "I don't know"

MEMORY:
{context}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]

    response = chat(model="qwen3:8b", messages=messages)

    text = response.message.content

    try:
        data = json.loads(text)
        return data.get("answer", text)
    except:
        return text
