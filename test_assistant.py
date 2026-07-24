import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.assistant import JarvisAssistant
from core.memory import MemoryManager
from core.intent import Intent


class AssistantIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.memory = MemoryManager(Path(self.temporary.name) / "memory.db")
        self.llm = Mock()
        self.llm.ask.return_value = "Answer"
        self.assistant = JarvisAssistant(self.memory, self.llm)
        self.assistant.actions._launcher = Mock()

    def tearDown(self) -> None:
        self.memory.close()
        self.temporary.cleanup()

    def test_deep_mode_is_forwarded_to_model(self) -> None:
        self.assertEqual(self.assistant.respond("deep mode"), "Deep intelligence mode enabled.")
        self.assistant.respond("Solve a hard problem")
        self.assertTrue(self.llm.ask.call_args.kwargs["deep_reasoning"])

    def test_one_time_deep_prefix_does_not_change_mode(self) -> None:
        self.assistant.respond("think deeply: solve this")
        self.assertEqual(self.llm.ask.call_args.args[0], "solve this")
        self.assertTrue(self.llm.ask.call_args.kwargs["deep_reasoning"])
        self.assertEqual(self.assistant.intelligence_mode, "fast")

    def test_informal_data_request_runs_safe_interpreted_action(self) -> None:
        csv_path = Path(self.temporary.name) / "sales.csv"
        csv_path.write_text("region,revenue\nNorth,100\nSouth,200\n", encoding="utf-8")
        self.assistant.analyst.handle(f'analyze "{csv_path}"')
        self.assistant.interpreter.interpret = Mock(
            return_value=Intent(
                action="grouped_analysis",
                value="revenue",
                group="region",
                operation="sum",
                confidence=0.95,
            )
        )

        response = self.assistant.respond("show sales by place")

        self.assertIn("I understood that as: grouped analysis", response)
        self.assertIn("South: 200.00", response)

    def test_low_confidence_intent_falls_back_to_chat(self) -> None:
        self.assistant.interpreter.interpret = Mock(
            return_value=Intent(action="generate_python", confidence=0.2)
        )
        response = self.assistant.respond("some python-ish thought")
        self.assertEqual(response, "Answer")

    def test_feedback_rates_previous_interaction(self) -> None:
        self.assistant.respond("Hello Jarvis")
        response = self.assistant.respond("good answer")
        self.assertIn("successful answer", response)
        self.assertEqual(self.memory.learning_stats()["positive"], 1)

    def test_taught_phrase_runs_learned_safe_command(self) -> None:
        csv_path = Path(self.temporary.name) / "sales.csv"
        csv_path.write_text("region,revenue\nNorth,100\nSouth,200\n", encoding="utf-8")
        self.assistant.analyst.handle(f'analyze "{csv_path}"')
        self.assistant.respond(
            "learn phrase: show me the cash => sum revenue by region"
        )
        response = self.assistant.respond("show me cash")
        self.assertIn("Using what you taught me", response)
        self.assertIn("South: 200.00", response)

    def test_low_risk_application_launches_immediately(self) -> None:
        completed = self.assistant.respond("open calculator")
        self.assertIn("Completed", completed)
        self.assistant.actions._launcher.assert_called_once_with(("calc.exe",), "process")
        self.assertEqual(self.memory.recent_actions()[0]["status"], "completed")

    def test_action_can_be_cancelled(self) -> None:
        self.assistant.actions.request("notepad")
        response = self.assistant.respond("cancel action")
        self.assertIn("Nothing was run", response)
        self.assistant.actions._launcher.assert_not_called()
        self.assertEqual(self.memory.recent_actions()[0]["status"], "cancelled")

    def test_wrong_action_id_cannot_confirm(self) -> None:
        self.assistant.actions.request("file_explorer")
        response = self.assistant.respond("confirm action wrong-id")
        self.assertIn("does not match", response)
        self.assistant.actions._launcher.assert_not_called()

    def test_calendar_action_and_common_misspelling_are_allowlisted(self) -> None:
        response = self.assistant.respond("open calender")
        self.assertIn("Completed: Open Calendar", response)
        self.assistant.actions._launcher.assert_called_once_with(("outlookcal:",), "shell")

    def test_unknown_application_does_not_fall_through_to_llm(self) -> None:
        self.assistant.actions.resolver.resolve = Mock(return_value=None)
        response = self.assistant.respond("open mystery app")
        self.assertIn("couldn't find an installed application", response)
        self.llm.ask.assert_not_called()

    def test_task_commands_create_pause_approve_and_persist(self) -> None:
        waiting = self.assistant.respond("create task: summarize notes; export report")
        self.assertIn("WAITING APPROVAL", waiting)
        task = self.assistant.tasks.get()
        self.assertEqual(task.completed_steps, 1)

        completed = self.assistant.respond(f"approve step {task.steps[1].id}")

        self.assertIn("COMPLETED", completed)
        self.assertIn(task.id, self.assistant.respond("show tasks"))

    def test_invalid_task_command_fails_without_llm_fallback(self) -> None:
        response = self.assistant.respond("task status missing")
        self.assertIn("Task request could not be completed", response)
        self.llm.ask.assert_not_called()


if __name__ == "__main__":
    unittest.main()
