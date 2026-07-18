import unittest
from unittest.mock import Mock

from core.intent import IntentInterpreter


class IntentInterpreterTests(unittest.TestCase):
    def test_parses_misspelled_grouped_request(self) -> None:
        llm = Mock()
        llm.ask.return_value = """```json
        {"action":"grouped_analysis","value":"revenue","group":"region",
         "operation":"sum","chart_type":"bar","request":"","confidence":0.91}
        ```"""
        interpreter = IntentInterpreter(llm)

        intent = interpreter.interpret(
            "show me da muney by place", ["region", "revenue"]
        )

        self.assertEqual(intent.action, "grouped_analysis")
        self.assertEqual(intent.value, "revenue")
        self.assertEqual(intent.group, "region")
        self.assertGreater(intent.confidence, 0.9)

    def test_invalid_model_output_falls_back_to_chat(self) -> None:
        llm = Mock()
        llm.ask.return_value = "I am not sure"
        intent = IntentInterpreter(llm).interpret("something unclear")
        self.assertEqual(intent.action, "chat")
        self.assertEqual(intent.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
