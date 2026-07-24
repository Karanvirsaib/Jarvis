import tempfile
import unittest
from pathlib import Path

from core.actions import ApplicationResolver


class ApplicationResolverTests(unittest.TestCase):
    def test_finds_start_menu_shortcut_by_friendly_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shortcut = root / "Visual Studio Code.lnk"
            shortcut.touch()
            result = ApplicationResolver((root,)).resolve("visual studio code")
            self.assertIsNotNone(result)
            self.assertEqual(result.target, str(shortcut))

    def test_rejects_weak_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "Completely Different Tool.lnk").touch()
            self.assertIsNone(ApplicationResolver((root,)).resolve("spotify"))


if __name__ == "__main__":
    unittest.main()
