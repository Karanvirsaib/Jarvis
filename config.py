"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("JARVIS_MODEL", "qwen3:8b")
    database_path: Path = Path(os.getenv("JARVIS_DATABASE", "data/jarvis.db"))
    speech_rate: int = int(os.getenv("JARVIS_SPEECH_RATE", "175"))
    listen_timeout: float = float(os.getenv("JARVIS_LISTEN_TIMEOUT", "5"))
    phrase_time_limit: float = float(os.getenv("JARVIS_PHRASE_TIME_LIMIT", "15"))
    ollama_keep_alive: str = os.getenv("JARVIS_OLLAMA_KEEP_ALIVE", "30m")
    max_response_tokens: int = int(os.getenv("JARVIS_MAX_RESPONSE_TOKENS", "192"))
    neural_voice: str = os.getenv("JARVIS_NEURAL_VOICE", "en-GB-RyanNeural")
    neural_voice_rate: str = os.getenv("JARVIS_NEURAL_VOICE_RATE", "+0%")
    neural_voice_pitch: str = os.getenv("JARVIS_NEURAL_VOICE_PITCH", "-2Hz")


settings = Settings()
