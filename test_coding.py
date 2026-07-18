import unittest
from unittest.mock import Mock

from core.coding import LocalCoder


class LocalCoderTests(unittest.TestCase):
    def test_python_generation_uses_deep_local_reasoning(self) -> None:
        llm = Mock()
        llm.ask.return_value = "```python\nprint('hello')\n```"
        coder = LocalCoder(llm)

        result = coder.generate_python("print hello")

        self.assertIn("python", result)
        self.assertTrue(llm.ask.call_args.kwargs["deep_reasoning"])

    def test_sql_prompt_contains_loaded_schema(self) -> None:
        llm = Mock()
        llm.ask.return_value = "SELECT region FROM data"
        coder = LocalCoder(llm)

        coder.generate_sql("show regions", ["region", "revenue"])

        prompt = llm.ask.call_args.args[0]
        self.assertIn("region, revenue", prompt)
        self.assertIn("read-only SQLite", prompt)


if __name__ == "__main__":
    unittest.main()
