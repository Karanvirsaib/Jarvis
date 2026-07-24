"""Application-facing task orchestration and presentation."""

from __future__ import annotations

from typing import Any

from core.tasks.models import StepStatus, Task, TaskStatus, TaskStep
from core.tasks.planner import ChecklistPlanner
from core.tasks.runner import TaskRunner
from core.tasks.store import JsonTaskStore, TaskNotFoundError
from core.tasks.tools import ToolRegistry, create_default_registry


TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}


class TaskService:
    def __init__(
        self,
        store: JsonTaskStore,
        tools: ToolRegistry | None = None,
        planner: ChecklistPlanner | None = None,
    ) -> None:
        self.store = store
        self.tools = tools or create_default_registry()
        self.planner = planner or ChecklistPlanner()
        self.runner = TaskRunner(store, self.tools)
        self.active_task_id = self._latest_active_id()

    def create(self, goal: str, *, run: bool = True) -> Task:
        task = self.planner.create_task(goal)
        self.store.save(task)
        self.active_task_id = task.id
        return self.runner.run(task) if run else task

    def preview(self, goal: str) -> Task:
        return self.planner.create_task(goal)

    def create_from_plan(
        self, goal: str, steps: list[dict[str, Any]], *, run: bool = True
    ) -> Task:
        if not isinstance(steps, list) or not 1 <= len(steps) <= 12:
            raise ValueError("A task plan must contain between 1 and 12 steps.")
        validated = []
        for item in steps:
            if not isinstance(item, dict):
                raise ValueError("Every task step must be an object.")
            title = str(item.get("title", "")).strip()
            tool = str(item.get("tool", "")).strip()
            arguments = item.get("arguments", {})
            definition = self.tools.definition(tool)
            # Validate names and required arguments without executing the handler.
            if not isinstance(arguments, dict):
                raise ValueError("Task tool arguments must be an object.")
            unknown = set(arguments) - set(definition.parameters)
            missing = set(definition.required_parameters) - set(arguments)
            if unknown or missing:
                raise ValueError(f"Invalid arguments for task tool: {tool}")
            validated.append(
                TaskStep(
                    title=title,
                    tool=tool,
                    arguments=arguments,
                    requires_approval=definition.requires_approval,
                )
            )
        task = Task(goal=goal, steps=validated)
        self.store.save(task)
        self.active_task_id = task.id
        return self.runner.run(task) if run else task

    def get(self, task_id: str | None = None) -> Task:
        resolved = task_id or self.active_task_id
        if not resolved:
            raise TaskNotFoundError("There is no active task.")
        return self.store.get(resolved)

    def list(self) -> list[Task]:
        return self.store.list()

    def resume(self, task_id: str | None = None) -> Task:
        task = self.get(task_id)
        self.active_task_id = task.id
        return self.runner.run(task)

    def approve(self, step_id: str, task_id: str | None = None) -> Task:
        task = self.get(task_id)
        self.runner.approve(task, step_id)
        return self.runner.run(self.store.get(task.id))

    def retry(self, step_id: str, task_id: str | None = None) -> Task:
        task = self.get(task_id)
        self.runner.retry(task, step_id)
        return self.runner.run(self.store.get(task.id))

    def cancel(self, task_id: str | None = None) -> Task:
        return self.runner.cancel(self.get(task_id))

    def snapshot(self, task: Task) -> dict[str, Any]:
        return {
            "id": task.id,
            "goal": task.goal,
            "status": task.status.value,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "progress": task.progress,
            "completed_steps": task.completed_steps,
            "total_steps": len(task.steps),
            "error": task.error,
            "steps": [
                {
                    "id": step.id,
                    "title": step.title,
                    "tool": step.tool,
                    "arguments": step.arguments,
                    "status": step.status.value,
                    "requires_approval": step.requires_approval,
                    "approved": step.approved,
                    "result": step.result,
                    "error": step.error,
                    "attempts": step.attempts,
                }
                for step in task.steps
            ],
        }

    def format(self, task: Task) -> str:
        symbols = {
            StepStatus.PENDING: "○",
            StepStatus.RUNNING: "●",
            StepStatus.WAITING_APPROVAL: "◇",
            StepStatus.COMPLETED: "✓",
            StepStatus.FAILED: "!",
            StepStatus.CANCELLED: "×",
        }
        lines = [
            f"TASK // {task.status.value.replace('_', ' ').upper()}",
            task.goal,
            f"ID: {task.id}",
            f"Progress: {task.completed_steps}/{len(task.steps)}",
            "",
        ]
        for step in task.steps:
            line = f"{symbols[step.status]} {step.title} [{step.status.value}]"
            if step.status is StepStatus.WAITING_APPROVAL:
                line += f" — approve step {step.id}"
            elif step.error:
                line += f" — {step.error}"
            lines.append(line)
        return "\n".join(lines)

    def format_list(self) -> str:
        tasks = self.list()
        if not tasks:
            return "No tasks have been created yet."
        return "TASK HISTORY\n" + "\n".join(
            f"- {task.status.value.upper()} | {task.goal} | {task.id}"
            for task in tasks[:20]
        )

    def _latest_active_id(self) -> str | None:
        for task in self.store.list():
            if task.status not in TERMINAL_TASK_STATUSES:
                return task.id
        return None
