import unittest
from unittest.mock import patch

from core.llm import LLMClient


class LLMClientTests(unittest.TestCase):
    @patch("core.llm.chat")
    def test_uses_low_latency_ollama_options(self, mocked_chat) -> None:
        mocked_chat.return_value.message.content = "Ready."
        client = LLMClient("qwen3:8b", keep_alive="30m", max_response_tokens=128)

        self.assertEqual(client.ask("Hello"), "Ready.")

        call = mocked_chat.call_args
        self.assertFalse(call.kwargs["think"])
        self.assertEqual(call.kwargs["keep_alive"], "30m")
        self.assertEqual(call.kwargs["options"]["num_predict"], 128)

    @patch("core.llm.chat")
    def test_deep_mode_enables_reasoning_and_larger_budget(self, mocked_chat) -> None:
        mocked_chat.return_value.message.content = "Reasoned answer."
        client = LLMClient(max_response_tokens=100)

        client.ask("Solve this", deep_reasoning=True)

        call = mocked_chat.call_args
        self.assertTrue(call.kwargs["think"])
        self.assertEqual(call.kwargs["options"]["num_predict"], 200)


if __name__ == "__main__":
    unittest.main()
