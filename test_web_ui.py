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


if __name__ == "__main__":
    unittest.main()
