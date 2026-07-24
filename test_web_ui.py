import unittest
from pathlib import Path


class WebUiRegressionTests(unittest.TestCase):
    def test_responses_support_selection_and_copy_fallback(self):
        root = Path(__file__).parent / "ui" / "web"
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        self.assertIn("navigator.clipboard", script)
        self.assertIn("document.execCommand('copy')", script)
        self.assertIn("replace(/^```", script)
        self.assertIn("addCopyButton(article,text)", script)
        self.assertIn("user-select:text", styles)

    def test_action_preview_has_confirmation_controls(self):
        root = Path(__file__).parent / "ui" / "web"
        script = (root / "app.js").read_text(encoding="utf-8")
        self.assertIn("addActionControls", script)
        self.assertIn("bridge.confirm_action(actionId)", script)
        self.assertIn("bridge.cancel_action(actionId)", script)
        self.assertNotIn("submit(`confirm action", script)

    def test_loading_states_use_accessible_skeletons(self):
        root = Path(__file__).parent / "ui" / "web"
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        self.assertIn("message-skeleton", script)
        self.assertIn("Jarvis is preparing a response", script)
        self.assertIn("aria-busy", script)
        self.assertIn("@media(prefers-reduced-motion:reduce)", styles)

    def test_ui_cache_is_versioned_bounded_and_restored(self):
        root = Path(__file__).parent / "ui" / "web"
        script = (root / "app.js").read_text(encoding="utf-8")
        self.assertIn("UI_CACHE_KEY='jarvis.ui.v1'", script)
        self.assertIn("MAX_CACHED_MESSAGES=60", script)
        self.assertIn("localStorage.setItem", script)
        self.assertIn("restoreUiCache();", script)
        self.assertIn("message-loading", script)

    def test_task_workspace_renders_lifecycle_controls(self):
        root = Path(__file__).parent / "ui" / "web"
        markup = (root / "index.html").read_text(encoding="utf-8")
        script = (root / "app.js").read_text(encoding="utf-8")
        styles = (root / "styles.css").read_text(encoding="utf-8")
        self.assertIn('id="task-panel"', markup)
        self.assertIn("refreshTasks", script)
        self.assertIn("approve_task_step", script)
        self.assertIn("retry_task_step", script)
        self.assertIn("cancel_task", script)
        self.assertIn(".task-panel.open", styles)

    def test_task_composer_requires_review_before_start(self):
        root = Path(__file__).parent / "ui" / "web"
        markup = (root / "index.html").read_text(encoding="utf-8")
        script = (root / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="task-composer"', markup)
        self.assertIn('id="plan-preview"', markup)
        self.assertIn("bridge.plan_task(goal)", script)
        self.assertIn("bridge.start_task", script)
        self.assertIn("renderPlanPreview", script)


if __name__ == "__main__":
    unittest.main()
