import logging
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

JARVIS_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(JARVIS_ROOT / ".env")

logger = logging.getLogger(__name__)


def get_openrouter_api_key() -> str | None:
    """Return a real-looking configured key, ignoring the checked-in placeholder."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key or any(marker in key.lower() for marker in ("your_", "placeholder", "replace_me", "paste_key")):
        return None
    return key

class HermesExecutiveAgent:
    """
    Text-model adapter for OpenRouter with a local Ollama fallback.

    This class does not implement Hermes Agent's tool loop; it only obtains a
    text response. Tool execution remains owned by the Jarvis orchestrator.
    """
    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "openrouter/free",
        fallback_provider: str = "ollama",
        fallback_model: str = "qwen3.5:4b",
        openrouter_url: str = "https://openrouter.ai/api/v1/chat/completions",
        ollama_url: str = "http://localhost:11434/api/generate",
        openrouter_timeout: int = 120,
        ollama_timeout: int = 180,
        context_length: int = 8192,
    ):
        self.provider = provider.lower()
        self.model = model
        self.fallback_provider = fallback_provider.lower()
        self.fallback_model = fallback_model
        self.openrouter_url = openrouter_url
        self.ollama_url = ollama_url
        self.openrouter_timeout = openrouter_timeout
        self.ollama_timeout = ollama_timeout
        self.context_length = context_length

    def check_health(self) -> bool:
        if self.provider == "openrouter" and get_openrouter_api_key():
            return True
        if self.fallback_provider == "ollama":
            try:
                response = requests.get(
                    self.ollama_url.rsplit("/api/", 1)[0] + "/api/tags", timeout=5
                )
                response.raise_for_status()
                installed = [m.get("name", "") for m in response.json().get("models", [])]
                return any(self.fallback_model in name for name in installed)
            except (requests.RequestException, ValueError):
                return False
        return False

    def think(self, prompt: str, system: str = "") -> str:
        """Get a response from the configured provider, then use local fallback."""
        if self.provider == "openrouter":
            api_key = get_openrouter_api_key()
            if api_key:
                try:
                    return self._think_openrouter(prompt, system, api_key)
                except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
                    logger.warning("OpenRouter request failed; trying configured fallback (%s).", exc)
            else:
                logger.info("OPENROUTER_API_KEY is not set; trying configured fallback.")

        if self.fallback_provider == "ollama":
            try:
                return self._think_ollama(prompt, system)
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
                logger.error("Local Ollama fallback failed: %s", exc)
                if self.provider == "openrouter" and not get_openrouter_api_key():
                    return "Brain unavailable: set OPENROUTER_API_KEY in D:\\Jarvis\\.env or start Ollama with the configured local model."
                return "Brain unavailable: OpenRouter and the configured local Ollama fallback both failed. Check D:\\Jarvis\\logs\\jarvis.log."

        return f"Brain unavailable: unsupported provider configuration '{self.provider}'."

    def _think_openrouter(self, prompt: str, system: str, api_key: str) -> str:
        payload = {
            "model": self.model,
            "messages": ([{"role": "system", "content": system}] if system else [])
                        + [{"role": "user", "content": prompt}],
            "stream": False,
        }
        response = requests.post(
            self.openrouter_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Jarvis",
            },
            timeout=self.openrouter_timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if isinstance(content, str) and content.strip():
            return content.strip()
        raise ValueError("OpenRouter returned no text content")

    def _think_ollama(self, prompt: str, system: str) -> str:
        payload: dict[str, Any] = {
            "model": self.fallback_model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"num_ctx": self.context_length},
        }
        try:
            response = requests.post(self.ollama_url, json=payload, timeout=self.ollama_timeout)
            response.raise_for_status()
            text = response.json().get("response", "")
            if text.strip():
                return text.strip()
            raise ValueError("Ollama returned no text")
        except requests.RequestException:
            raise
