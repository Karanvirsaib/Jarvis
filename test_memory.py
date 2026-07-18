import tempfile
import threading
import unittest
from pathlib import Path

from core.memory import MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = MemoryManager(Path(self.temp_dir.name) / "test.db")

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_remember_recall_and_forget(self) -> None:
        self.memory.remember("Name", "Karan")
        self.assertEqual(self.memory.recall("name"), "Karan")
        self.assertTrue(self.memory.forget("name"))
        self.assertIsNone(self.memory.recall("name"))

    def test_extracts_name(self) -> None:
        result = self.memory.extract_and_store("My name is Karan")
        self.assertIn("Karan", result or "")
        self.assertEqual(self.memory.recall("name"), "Karan")

    def test_memory_can_be_used_from_worker_thread(self) -> None:
        worker = threading.Thread(target=self.memory.remember, args=("mode", "desktop"))
        worker.start()
        worker.join()
        self.assertEqual(self.memory.recall("mode"), "desktop")

    def test_learns_and_fuzzily_recalls_custom_command(self) -> None:
        self.memory.learn_command("show me the cash", "sum revenue by region")
        self.assertEqual(
            self.memory.recall_learned_command("show me cash"),
            "sum revenue by region",
        )

    def test_positive_interaction_becomes_relevant_example(self) -> None:
        interaction = self.memory.record_interaction(
            "How should I clean sales data?", "Validate columns and missing values."
        )
        self.memory.rate_interaction(interaction, 1)
        examples = self.memory.relevant_successes("clean my sales data")
        self.assertEqual(len(examples), 1)
        self.assertIn("Validate columns", examples[0][1])

    def test_clear_learning_preserves_personal_memory(self) -> None:
        self.memory.remember("name", "Karan")
        self.memory.learn_command("cash", "data summary")
        self.memory.record_interaction("hello", "hi")
        self.memory.clear_learning()
        self.assertEqual(self.memory.recall("name"), "Karan")
        self.assertEqual(self.memory.learning_stats()["interactions"], 0)
        self.assertIsNone(self.memory.recall_learned_command("cash"))


if __name__ == "__main__":
    unittest.main()
