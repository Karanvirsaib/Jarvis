"""Sequential, checkpointed execution for durable Jarvis tasks."""

from __future__ import annotations

from core.tasks.models import StepStatus, Task, TaskStatus
from core.tasks.store import JsonTaskStore
from core.tasks.tools import ToolRegistry


class InvalidTaskTransitionError(ValueError):
    pass


class TaskRunner:
    def __init__(self, store: JsonTaskStore, tools: ToolRegistry) -> None:
        self.store = store
        self.tools = tools

    def run(self, task: Task) -> Task:
        if task.status is TaskStatus.CANCELLED:
            raise InvalidTaskTransitionError("A cancelled task cannot be resumed.")
        if task.status is TaskStatus.COMPLETED:
            return task

        # A process may have stopped after persisting RUNNING but before a result.
        for step in task.steps:
            if step.status is StepStatus.RUNNING:
                step.status = StepStatus.PENDING

        task.status = TaskStatus.RUNNING
        task.error = None
        self._save(task)

        for step in task.steps:
            if step.status is StepStatus.COMPLETED:
                continue
            if step.status is StepStatus.CANCELLED:
                task.status = TaskStatus.CANCELLED
                self._save(task)
                return task
            if step.status is StepStatus.FAILED:
                task.status = TaskStatus.FAILED
                task.error = step.error
                self._save(task)
                return task

            try:
                needs_approval = (
                    step.requires_approval
                    or self.tools.requires_approval(step.tool)
                )
            except Exception as exc:
                self._fail_step(task, step, exc)
                return task

            if needs_approval and not step.approved:
                step.status = StepStatus.WAITING_APPROVAL
                task.status = TaskStatus.WAITING_APPROVAL
                self._save(task)
                return task

            step.status = StepStatus.RUNNING
            step.attempts += 1
            step.error = None
            self._save(task)
            try:
                step.result = self.tools.execute(step.tool, step.arguments)
            except Exception as exc:
                self._fail_step(task, step, exc)
                return task
            step.status = StepStatus.COMPLETED
            self._save(task)

        task.status = TaskStatus.COMPLETED
        self._save(task)
        return task

    def approve(self, task: Task, step_id: str) -> Task:
        step = self._step(task, step_id)
        if step.status is not StepStatus.WAITING_APPROVAL:
            raise InvalidTaskTransitionError("The step is not waiting for approval.")
        step.approved = True
        step.status = StepStatus.PENDING
        task.status = TaskStatus.PENDING
        self._save(task)
        return task

    def retry(self, task: Task, step_id: str) -> Task:
        step = self._step(task, step_id)
        if step.status is not StepStatus.FAILED:
            raise InvalidTaskTransitionError("Only a failed step can be retried.")
        step.status = StepStatus.PENDING
        step.error = None
        step.result = None
        task.status = TaskStatus.PENDING
        task.error = None
        self._save(task)
        return task

    def cancel(self, task: Task) -> Task:
        if task.status is TaskStatus.COMPLETED:
            raise InvalidTaskTransitionError("A completed task cannot be cancelled.")
        for step in task.steps:
            if step.status not in {StepStatus.COMPLETED, StepStatus.FAILED}:
                step.status = StepStatus.CANCELLED
        task.status = TaskStatus.CANCELLED
        self._save(task)
        return task

    @staticmethod
    def _step(task: Task, step_id: str):
        for step in task.steps:
            if step.id == step_id:
                return step
        raise LookupError(f"Step not found: {step_id}")

    def _fail_step(self, task: Task, step, exc: Exception) -> None:
        step.status = StepStatus.FAILED
        step.error = f"{type(exc).__name__}: {exc}"
        task.status = TaskStatus.FAILED
        task.error = step.error
        self._save(task)

    def _save(self, task: Task) -> None:
        self.store.save(task)
