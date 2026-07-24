import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.tasks import (
    ChecklistPlanner,
    InvalidTaskTransitionError,
    IntelligentPlanner,
    JsonTaskStore,
    StepStatus,
    Task,
    TaskNotFoundError,
    TaskStatus,
    TaskStep,
    TaskStoreCorruptionError,
    TaskStoreError,
    TaskRunner,
    TaskService,
    ToolRegistry,
    UnknownToolError,
    create_default_registry,
)


class TaskModelTests(unittest.TestCase):
    def test_task_round_trip_preserves_lifecycle_data(self) -> None:
        step = TaskStep("Analyze dataset", "analyze", {"path": "sales.csv"})
        step.status = StepStatus.COMPLETED
        step.result = {"rows": 20}
        step.attempts = 1
        task = Task("Create a sales report", [step], status=TaskStatus.RUNNING)

        restored = Task.from_dict(task.to_dict())

        self.assertEqual(restored.goal, task.goal)
        self.assertIs(restored.status, TaskStatus.RUNNING)
        self.assertIs(restored.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(restored.steps[0].result, {"rows": 20})
        self.assertEqual(restored.progress, 1.0)

    def test_task_rejects_empty_or_duplicate_steps(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one step"):
            Task("Empty plan", [])
        step = TaskStep("First", "capture")
        with self.assertRaisesRegex(ValueError, "unique"):
            Task("Bad plan", [step, step])


class JsonTaskStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "state" / "tasks.json"
        self.store = JsonTaskStore(self.path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_save_get_and_list_use_versioned_document(self) -> None:
        older = Task("First task", [TaskStep("One", "capture")])
        newer = Task("Second task", [TaskStep("Two", "capture")])
        self.store.save(older)
        self.store.save(newer)

        self.assertEqual(self.store.get(older.id).goal, "First task")
        self.assertEqual([task.id for task in self.store.list()], [newer.id, older.id])
        document = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(document["version"], 1)
        self.assertEqual(set(document["tasks"]), {older.id, newer.id})
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_missing_task_has_specific_error(self) -> None:
        with self.assertRaisesRegex(TaskNotFoundError, "missing"):
            self.store.get("missing")

    def test_corrupt_store_is_reported_without_overwrite(self) -> None:
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{broken", encoding="utf-8")

        with self.assertRaises(TaskStoreCorruptionError):
            self.store.list()
        with self.assertRaises(TaskStoreCorruptionError):
            self.store.save(Task("Safe task", [TaskStep("One", "capture")]))
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{broken")

    def test_non_json_result_does_not_replace_existing_store(self) -> None:
        safe = Task("Safe task", [TaskStep("One", "capture")])
        self.store.save(safe)
        before = self.path.read_bytes()
        unsafe = Task("Unsafe task", [TaskStep("Two", "capture")])
        unsafe.steps[0].result = object()

        with self.assertRaises(TaskStoreError):
            self.store.save(unsafe)

        self.assertEqual(self.path.read_bytes(), before)


class TaskExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = JsonTaskStore(Path(self.temporary.name) / "tasks.json")
        self.tools = create_default_registry()
        self.runner = TaskRunner(self.store, self.tools)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_planner_splits_checklist_and_marks_risky_steps(self) -> None:
        task = ChecklistPlanner().create_task("Summarize notes; export report")

        self.assertEqual(len(task.steps), 2)
        self.assertFalse(task.steps[0].requires_approval)
        self.assertTrue(task.steps[1].requires_approval)

    def test_runner_checkpoints_and_completes_safe_steps(self) -> None:
        task = Task("Process text", [TaskStep("Capture", "report", {"message": "done"})])

        result = self.runner.run(task)

        self.assertIs(result.status, TaskStatus.COMPLETED)
        self.assertEqual(result.steps[0].result, "done")
        self.assertEqual(result.steps[0].attempts, 1)
        self.assertIs(self.store.get(task.id).status, TaskStatus.COMPLETED)

    def test_tool_metadata_forces_approval(self) -> None:
        calls = []
        self.tools.register(
            "publish", lambda value: calls.append(value), requires_approval=True
        )
        task = Task("Publish", [TaskStep("Publish", "publish", {"value": "report"})])

        waiting = self.runner.run(task)
        self.assertIs(waiting.status, TaskStatus.WAITING_APPROVAL)
        self.assertEqual(calls, [])

        self.runner.approve(waiting, waiting.steps[0].id)
        completed = self.runner.run(self.store.get(task.id))
        self.assertIs(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(calls, ["report"])

    def test_unknown_tool_fails_visibly(self) -> None:
        task = Task("Unsafe", [TaskStep("Shell", "shell")])

        result = self.runner.run(task)

        self.assertIs(result.status, TaskStatus.FAILED)
        self.assertIn("UnknownToolError", result.steps[0].error)
        self.assertEqual(result.steps[0].attempts, 0)

    def test_failed_step_can_be_retried_without_repeating_completed_step(self) -> None:
        calls = []

        def flaky(value):
            calls.append(value)
            if calls.count("second") == 1:
                raise RuntimeError("temporary")
            return value

        self.tools.register("flaky", flaky)
        task = Task(
            "Retry workflow",
            [
                TaskStep("First", "flaky", {"value": "first"}),
                TaskStep("Second", "flaky", {"value": "second"}),
            ],
        )
        failed = self.runner.run(task)
        self.runner.retry(failed, failed.steps[1].id)
        completed = self.runner.run(self.store.get(task.id))

        self.assertIs(completed.status, TaskStatus.COMPLETED)
        self.assertEqual(calls, ["first", "second", "second"])
        self.assertEqual(completed.steps[0].attempts, 1)
        self.assertEqual(completed.steps[1].attempts, 2)

    def test_task_can_be_cancelled_but_not_resumed(self) -> None:
        task = Task("Stop", [TaskStep("Wait", "report", {"message": "no"})])
        cancelled = self.runner.cancel(task)

        self.assertIs(cancelled.status, TaskStatus.CANCELLED)
        self.assertIs(cancelled.steps[0].status, StepStatus.CANCELLED)
        with self.assertRaises(InvalidTaskTransitionError):
            self.runner.run(cancelled)

    def test_registry_rejects_unknown_and_duplicate_tools(self) -> None:
        registry = ToolRegistry()
        registry.register("one", lambda: 1)
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.register("one", lambda: 2)
        with self.assertRaisesRegex(UnknownToolError, "shell"):
            registry.execute("shell", {})

    def test_registry_validates_declared_arguments(self) -> None:
        registry = ToolRegistry()
        registry.register("join", lambda first, second="b": first + second)
        self.assertEqual(registry.execute("join", {"first": "a"}), "ab")
        with self.assertRaisesRegex(ValueError, "Unknown arguments"):
            registry.execute("join", {"first": "a", "secret": "x"})
        with self.assertRaisesRegex(ValueError, "Missing arguments"):
            registry.execute("join", {})

    def test_intelligent_planner_accepts_only_registered_tool_schema(self) -> None:
        llm = Mock()
        llm.ask.return_value = json.dumps(
            {
                "steps": [
                    {
                        "title": "Save chart",
                        "tool": "chart",
                        "arguments": {"value": "sales"},
                    }
                ]
            }
        )
        registry = ToolRegistry()
        registry.register(
            "chart",
            lambda value: value,
            requires_approval=True,
            description="Save a chart.",
        )

        steps = IntelligentPlanner(llm, registry).plan("Create a sales chart")

        self.assertEqual(steps[0].tool, "chart")
        self.assertTrue(steps[0].requires_approval)

    def test_intelligent_planner_falls_back_on_invented_tool(self) -> None:
        llm = Mock()
        llm.ask.return_value = '{"steps":[{"title":"Hack","tool":"shell","arguments":{}}]}'
        registry = create_default_registry()

        steps = IntelligentPlanner(llm, registry).plan("Summarize safely")

        self.assertEqual(steps[0].tool, "report")

    def test_service_recovers_latest_non_terminal_task(self) -> None:
        waiting = ChecklistPlanner().create_task("Export report")
        self.store.save(waiting)
        self.runner.run(waiting)

        recovered = TaskService(self.store)

        self.assertEqual(recovered.active_task_id, waiting.id)
        self.assertIs(recovered.get().status, TaskStatus.WAITING_APPROVAL)
        self.assertEqual(recovered.snapshot(recovered.get())["total_steps"], 1)

    def test_reviewed_plan_is_revalidated_before_start(self) -> None:
        service = TaskService(self.store)
        task = service.create_from_plan(
            "Reviewed goal",
            [{"title": "Record", "tool": "report", "arguments": {"message": "done"}}],
        )
        self.assertIs(task.status, TaskStatus.COMPLETED)
        with self.assertRaises(UnknownToolError):
            service.create_from_plan(
                "Unsafe goal",
                [{"title": "Run", "tool": "shell", "arguments": {}}],
            )


if __name__ == "__main__":
    unittest.main()
