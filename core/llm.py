"""Local language-model client."""

from collections.abc import Iterable
import threading

from ollama import chat


SYSTEM_PROMPT = """You are Jarvis, a capable local personal assistant.
Be concise, practical, and conversational. Use saved memory only when relevant.
Never claim that you performed an action you did not perform.
For data questions, explain conclusions in plain language and mention limitations.
Never invent facts or present assumptions as true. When a question requires current
information, external verification, or knowledge you are not confident about, return
exactly `NEEDS_WEB: <focused search query>` instead of attempting an answer.

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
        self._warm_complete = threading.Event()
        self._warm_ok = False

    def warm_up(self) -> bool:
        """Load the model into Ollama without blocking desktop startup."""
        try:
            chat(
                model=self.model,
                messages=[{"role": "user", "content": "Reply with one word: ready"}],
                think=False,
                keep_alive=self.keep_alive,
                options={"num_predict": 1, "temperature": 0},
            )
            self._warm_ok = True
            return True
        except Exception:
            return False
        finally:
            self._warm_complete.set()

    def warm_status(self) -> dict[str, bool]:
        return {"complete": self._warm_complete.is_set(), "ready": self._warm_ok}

    def ask(
        self,
        user_input: str,
        memory: str = "",
        history: Iterable[dict[str, str]] = (),
        deep_reasoning: bool = False,
        response_tokens: int | None = None,
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
                "num_predict": (response_tokens or self.max_response_tokens) * (2 if deep_reasoning else 1),
                "temperature": 0.5 if deep_reasoning else 0.4,
            },
        )
        self._warm_ok = True
        self._warm_complete.set()
        return response.message.content.strip()


def ask_llm(user_input: str, context: str = "") -> str:
    """Backward-compatible wrapper for the original prototype."""
    return LLMClient().ask(user_input, context)
