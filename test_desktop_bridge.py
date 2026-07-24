import sys
import types
import unittest
import inspect
from unittest.mock import patch

from ui.desktop import JarvisBridge


class AssistantStub:
    class Actions:
        @staticmethod
        def status(): return None
        @staticmethod
        def confirm(action_id): return f"Completed: {action_id}."
        @staticmethod
        def cancel(): return "Cancelled."
    actions = Actions()
    class Tasks:
        task = types.SimpleNamespace(id="task-1")
        @classmethod
        def create(cls, goal): return cls.task
        @classmethod
        def preview(cls, goal): return cls.task
        @classmethod
        def create_from_plan(cls, goal, steps): return cls.task
        @classmethod
        def get(cls, task_id=None): return cls.task
        @classmethod
        def list(cls): return [cls.task]
        @classmethod
        def resume(cls, task_id=None): return cls.task
        @classmethod
        def approve(cls, step_id, task_id=None): return cls.task
        @classmethod
        def retry(cls, step_id, task_id=None): return cls.task
        @classmethod
        def cancel(cls, task_id=None): return cls.task
        @staticmethod
        def snapshot(task): return {"id": task.id, "status": "pending"}
    tasks = Tasks()
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

    def test_action_controls_use_silent_bridge_methods(self):
        bridge = JarvisBridge(AssistantStub())
        bridge._assistant.actions.status = lambda: {"id": "abc"}
        self.assertEqual(bridge.confirm_action("abc")["ok"], "true")
        self.assertEqual(bridge.cancel_action("abc")["ok"], "true")

    def test_task_lifecycle_is_exposed_as_structured_bridge_data(self):
        bridge = JarvisBridge(AssistantStub())
        self.assertEqual(bridge.create_task("Build report")["task"]["id"], "task-1")
        self.assertEqual(bridge.plan_task("Build report")["task"]["id"], "task-1")
        self.assertEqual(bridge.start_task("Build report", [])["task"]["id"], "task-1")
        self.assertEqual(bridge.task_status()["task"]["status"], "pending")
        self.assertEqual(bridge.list_tasks()["tasks"][0]["id"], "task-1")
        self.assertEqual(bridge.approve_task_step("step-1")["ok"], "true")
        self.assertEqual(bridge.retry_task_step("step-1")["ok"], "true")
        self.assertEqual(bridge.cancel_task()["ok"], "true")


if __name__ == "__main__":
    unittest.main()
