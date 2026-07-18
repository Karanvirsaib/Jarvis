"""Local language-model client."""

from collections.abc import Iterable

from ollama import chat


SYSTEM_PROMPT = """You are Jarvis, a capable local personal assistant.
Be concise, practical, and conversational. Use saved memory only when relevant.
Never claim that you performed an action you did not perform.
For data questions, explain conclusions in plain language and mention limitations.

Saved memory:
{memory}
"""


class LLMClient:
    def __init__(
        self,
        model: str = "qwen3:8b",
        keep_alive: str = "30m",
        max_response_tokens: int = 384,
    ) -> None:
        self.model = model
        self.keep_alive = keep_alive
        self.max_response_tokens = max_response_tokens

    def ask(
        self,
        user_input: str,
        memory: str = "",
        history: Iterable[dict[str, str]] = (),
        deep_reasoning: bool = False,
    ) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(memory=memory)},
            *history,
            {"role": "user", "content": user_input},
        ]
        response = chat(
            model=self.model,
            messages=messages,
            think=deep_reasoning,
            keep_alive=self.keep_alive,
            options={
                "num_predict": self.max_response_tokens * (2 if deep_reasoning else 1),
                "temperature": 0.5 if deep_reasoning else 0.4,
            },
        )
        return response.message.content.strip()


def ask_llm(user_input: str, context: str = "") -> str:
    """Backward-compatible wrapper for the original prototype."""
    return LLMClient().ask(user_input, context)
