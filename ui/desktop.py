"""Native WebView host for the Obsidian Jarvis interface."""

from __future__ import annotations

from pathlib import Path
import threading

from config import settings
from core.assistant import JarvisAssistant


WEB_ROOT = Path(__file__).with_name("web")


class JarvisBridge:
    """Small, explicit bridge between the HTML interface and Python engine."""

    def __init__(self, assistant: JarvisAssistant) -> None:
        self.assistant = assistant
        self.window = None
        self.voice = None

    def respond(self, command: str) -> dict[str, str]:
        try:
            answer = self.assistant.respond(command.strip())
            return {"ok": "true", "answer": answer}
        except Exception as exc:
            return {"ok": "false", "answer": f"I couldn't complete that request: {exc}"}

    def set_mode(self, mode: str) -> dict[str, str]:
        try:
            return {"ok": "true", "message": self.assistant.set_intelligence_mode(mode)}
        except ValueError as exc:
            return {"ok": "false", "message": str(exc)}

    def choose_dataset(self) -> dict[str, str]:
        if self.window is None:
            return {"ok": "false", "path": ""}

    def choose_resume(self) -> dict[str, str]:
        if self.window is None:
            return {"ok": "false", "path": ""}
        try:
            import webview
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Resume files (*.docx;*.pdf;*.txt)", "All files (*.*)"),
            )
            path = result[0] if result else ""
            return {"ok": "true" if path else "false", "path": path}
        except Exception:
            return {"ok": "false", "path": ""}
        try:
            import webview
            result = self.window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Data files (*.csv;*.xlsx;*.xlsm)", "All files (*.*)"),
            )
            path = result[0] if result else ""
            return {"ok": "true" if path else "false", "path": path}
        except Exception:
            return {"ok": "false", "path": ""}

    def listen(self) -> dict[str, str]:
        try:
            text = self._voice().listen(settings.listen_timeout, settings.phrase_time_limit)
            return {"ok": "true" if text else "false", "text": text or ""}
        except Exception as exc:
            return {"ok": "false", "text": str(exc)}

    def speak(self, text: str) -> dict[str, str]:
        def worker() -> None:
            try:
                self._voice().speak(text)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": "true"}

    def _voice(self):
        if self.voice is None:
            from voice.speech import VoiceInterface
            self.voice = VoiceInterface(
                settings.speech_rate, settings.neural_voice,
                settings.neural_voice_rate, settings.neural_voice_pitch,
            )
        return self.voice


def run_desktop(assistant: JarvisAssistant) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "The Obsidian interface requires pywebview. Run: "
            "python -m pip install -r requirements.txt"
        ) from exc

    bridge = JarvisBridge(assistant)
    window = webview.create_window(
        "JARVIS — Obsidian",
        url=WEB_ROOT.joinpath("index.html").resolve().as_uri(),
        js_api=bridge,
        width=1460,
        height=900,
        min_size=(1100, 700),
        background_color="#05080D",
    )
    bridge.window = window
    webview.start(debug=False)
