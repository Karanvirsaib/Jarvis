"""Microphone input with neural and offline speech output."""

import asyncio
import html
from pathlib import Path
import re
import tempfile
import threading
from typing import Any


def prepare_for_speech(text: str) -> str:
    """Turn display-oriented assistant output into natural spoken prose."""
    if not text or not text.strip():
        return ""

    spoken = html.unescape(text)

    # Code is useful on screen but painful when read character by character.
    code_blocks = re.findall(r"```[\s\S]*?```", spoken)
    spoken = re.sub(r"```[\s\S]*?```", " I've displayed the code on screen. ", spoken)

    # Remove formatting while retaining the words users actually need to hear.
    spoken = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", spoken)
    spoken = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", spoken)
    spoken = re.sub(r"https?://\S+|www\.\S+", "the link shown on screen", spoken)
    spoken = re.sub(r"`([^`]+)`", r"\1", spoken)
    spoken = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", spoken)
    spoken = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", spoken)
    spoken = re.sub(r"(?m)^\s*>\s?", "", spoken)
    spoken = re.sub(r"[*_~]{1,3}", "", spoken)

    # UI/status separators should create a pause, not be pronounced.
    spoken = spoken.replace("//", ". ").replace("::", ". ")
    spoken = re.sub(r"[│┃┆┊─━═]{2,}", ". ", spoken)
    spoken = re.sub(r"[◈◇◉◎●○⌁⌗]+", " ", spoken)
    spoken = spoken.replace("</>", "code")
    spoken = spoken.replace("=>", "means").replace("->", "to")
    spoken = re.sub(r"(?<=\w)[_/\\|](?=\w)", " ", spoken)

    # Convert line-oriented output into sentences with human-sized pauses.
    lines = [line.strip(" \t-•") for line in spoken.splitlines() if line.strip(" \t-•")]
    spoken = ". ".join(line.rstrip(" .") for line in lines)
    spoken = re.sub(r"\s+", " ", spoken).strip()
    spoken = re.sub(r"(?:\.\s*){2,}", ". ", spoken)
    spoken = re.sub(r"\s+([,.;:!?])", r"\1", spoken)

    if code_blocks and not spoken:
        return "I've displayed the code on screen."
    if spoken and spoken[-1] not in ".!?":
        spoken += "."
    return spoken


class VoiceInterface:
    def __init__(
        self,
        rate: int = 175,
        neural_voice: str = "en-GB-RyanNeural",
        neural_rate: str = "+0%",
        neural_pitch: str = "-2Hz",
    ) -> None:
        try:
            import pyttsx3
            import speech_recognition as sr
        except ImportError as exc:
            raise RuntimeError("Voice dependencies are missing.") from exc
        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.engine: Any = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.neural_voice = neural_voice
        self.neural_rate = neural_rate
        self.neural_pitch = neural_pitch
        self._speech_lock = threading.Lock()

    def speak(self, text: str) -> None:
        """Use a natural neural voice, falling back to offline Windows speech."""
        speech_text = prepare_for_speech(text)
        if not speech_text:
            return
        with self._speech_lock:
            try:
                asyncio.run(self._speak_neural(speech_text))
            except Exception:
                self.engine.say(speech_text)
                self.engine.runAndWait()

    async def _speak_neural(self, text: str) -> None:
        import edge_tts
        import pygame

        temporary = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        path = Path(temporary.name)
        temporary.close()
        try:
            communication = edge_tts.Communicate(
                text,
                self.neural_voice,
                rate=self.neural_rate,
                pitch=self.neural_pitch,
            )
            await communication.save(str(path))
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
            pygame.mixer.music.unload()
        finally:
            path.unlink(missing_ok=True)

    def listen(self, timeout: float = 5, phrase_time_limit: float = 15) -> str:
        try:
            with self.sr.Microphone() as source:
                print("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            return self.recognizer.recognize_google(audio).strip()
        except self.sr.WaitTimeoutError:
            return ""
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as exc:
            raise RuntimeError(f"Speech recognition service failed: {exc}") from exc
