import sys
import types
import unittest
import inspect
from unittest.mock import patch

from ui.desktop import JarvisBridge


class AssistantStub:
    def respond(self, command): return f"received: {command}"
    def set_intelligence_mode(self, mode): return f"{mode} enabled"


class WindowStub:
    def __init__(self, selected): self.selected = selected; self.shown = False
    def create_file_dialog(self, *_args, **_kwargs): return [self.selected]
    def show(self): self.shown = True


class VoiceStub:
    def listen(self, timeout, phrase_limit): return "system status"


class DesktopBridgeTests(unittest.TestCase):
    def setUp(self):
        self.webview = types.SimpleNamespace(OPEN_DIALOG="open")

    def test_respond_is_public_and_callable(self):
        bridge = JarvisBridge(AssistantStub())
        self.assertEqual(bridge.respond("system status")["answer"], "received: system status")

    def test_public_bridge_surface_contains_methods_only(self):
        bridge = JarvisBridge(AssistantStub())
        public = [getattr(bridge, name) for name in dir(bridge) if not name.startswith("_")]
        self.assertTrue(public)
        self.assertTrue(all(inspect.ismethod(value) for value in public))

    def test_ready_reveals_window_after_handshake(self):
        bridge = JarvisBridge(AssistantStub())
        bridge._window = WindowStub("")
        self.assertEqual(bridge.ready(), {"ok": "true"})
        self.assertTrue(bridge._window.shown)

    def test_listen_is_public_and_returns_transcript(self):
        bridge = JarvisBridge(AssistantStub())
        bridge._voice_client = VoiceStub()
        self.assertEqual(bridge.listen(), {"ok": "true", "text": "system status"})

    def test_dataset_and_resume_dialogs_are_independent(self):
        bridge = JarvisBridge(AssistantStub())
        with patch.dict(sys.modules, {"webview": self.webview}):
            bridge._window = WindowStub("sample.csv")
            self.assertEqual(bridge.choose_dataset()["path"], "sample.csv")
            bridge._window = WindowStub("resume.docx")
            self.assertEqual(bridge.choose_resume()["path"], "resume.docx")


if __name__ == "__main__":
    unittest.main()
