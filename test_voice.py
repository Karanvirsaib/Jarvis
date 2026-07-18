import unittest

from voice.speech import prepare_for_speech


class NaturalSpeechTests(unittest.TestCase):
    def test_removes_markdown_and_status_punctuation(self) -> None:
        text = "## SYSTEM STATUS // 10:30\n- **Memory:** online\n- [Report](https://example.com)"
        spoken = prepare_for_speech(text)
        self.assertNotIn("//", spoken)
        self.assertNotIn("**", spoken)
        self.assertNotIn("https", spoken)
        self.assertIn("SYSTEM STATUS", spoken)
        self.assertIn("Memory: online", spoken)

    def test_replaces_code_block_with_short_spoken_notice(self) -> None:
        spoken = prepare_for_speech("Here you go:\n```python\nprint('hello')\n```")
        self.assertNotIn("print", spoken)
        self.assertIn("displayed the code on screen", spoken)

    def test_turns_list_lines_into_sentences(self) -> None:
        spoken = prepare_for_speech("- First task\n- Second task")
        self.assertEqual(spoken, "First task. Second task.")


if __name__ == "__main__":
    unittest.main()
