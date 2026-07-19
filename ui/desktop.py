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
        # Pywebview recursively exposes public attributes. Keep implementation
        # objects private so it only inspects the explicit methods below.
        self._assistant = assistant
        self._window = None
        self._voice_client = None

    def ready(self) -> dict[str, str]:
        """Reveal the desktop only after JavaScript can call the full bridge."""
        if self._window is None:
            return {"ok": "false"}
        self._window.show()
        return {"ok": "true"}

    def model_status(self) -> dict[str, str]:
        status = self._assistant.llm.warm_status()
        return {
            "complete": "true" if status["complete"] else "false",
            "ready": "true" if status["ready"] else "false",
        }

    def respond(self, command: str) -> dict[str, str]:
        try:
            answer = self._assistant.respond(command.strip())
            return {"ok": "true", "answer": answer}
        except Exception as exc:
            return {"ok": "false", "answer": f"I couldn't complete that request: {exc}"}

    def set_mode(self, mode: str) -> dict[str, str]:
        try:
            return {"ok": "true", "message": self._assistant.set_intelligence_mode(mode)}
        except ValueError as exc:
            return {"ok": "false", "message": str(exc)}

    def choose_dataset(self) -> dict[str, str]:
        if self._window is None:
            return {"ok": "false", "path": ""}
        try:
            import webview
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Data files (*.csv;*.xlsx;*.xlsm)", "All files (*.*)"),
            )
            path = result[0] if result else ""
            return {"ok": "true" if path else "false", "path": path}
        except Exception:
            return {"ok": "false", "path": ""}

    def choose_resume(self) -> dict[str, str]:
        if self._window is None:
            return {"ok": "false", "path": ""}
        try:
            import webview
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Resume files (*.docx;*.pdf;*.txt)", "All files (*.*)"),
            )
            path = result[0] if result else ""
            return {"ok": "true" if path else "false", "path": path}
        except Exception:
            return {"ok": "false", "path": ""}

    def listen(self) -> dict[str, str]:
        try:
            text = self._get_voice().listen(settings.listen_timeout, settings.phrase_time_limit)
            return {"ok": "true" if text else "false", "text": text or ""}
        except Exception as exc:
            return {"ok": "false", "text": str(exc)}

    def speak(self, text: str) -> dict[str, str]:
        def worker() -> None:
            try:
                self._get_voice().speak(text)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
        return {"ok": "true"}

    def _get_voice(self):
        if self._voice_client is None:
            from voice.speech import VoiceInterface
            self._voice_client = VoiceInterface(
                settings.speech_rate, settings.neural_voice,
                settings.neural_voice_rate, settings.neural_voice_pitch,
            )
        return self._voice_client


def run_desktop(assistant: JarvisAssistant) -> None:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError(
            "The Obsidian interface requires pywebview. Run: "
            "python -m pip install -r requirements.txt"
        ) from exc

    threading.Thread(target=assistant.llm.warm_up, daemon=True, name="jarvis-model-warmup").start()
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
    bridge._window = window
    webview.start(debug=False)
