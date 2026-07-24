"""Serializable task and step lifecycle models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class TaskStep:
    title: str
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    id: str = field(default_factory=lambda: uuid4().hex)
    status: StepStatus = StepStatus.PENDING
    approved: bool = False
    result: Any = None
    error: str | None = None
    attempts: int = 0

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.tool = self.tool.strip()
        if not self.title:
            raise ValueError("Task step title cannot be empty.")
        if not self.tool:
            raise ValueError("Task step tool cannot be empty.")
        if not isinstance(self.arguments, dict):
            raise TypeError("Task step arguments must be a dictionary.")
        if self.attempts < 0:
            raise ValueError("Task step attempts cannot be negative.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskStep:
        payload = dict(data)
        payload["status"] = StepStatus(payload.get("status", StepStatus.PENDING))
        return cls(**payload)


@dataclass(slots=True)
class Task:
    goal: str
    steps: list[TaskStep]
    id: str = field(default_factory=lambda: uuid4().hex)
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    error: str | None = None

    def __post_init__(self) -> None:
        self.goal = self.goal.strip()
        if not self.goal:
            raise ValueError("Task goal cannot be empty.")
        if not self.steps:
            raise ValueError("A task must contain at least one step.")
        if len({step.id for step in self.steps}) != len(self.steps):
            raise ValueError("Task step IDs must be unique.")

    def touch(self) -> None:
        self.updated_at = utc_now()

    @property
    def completed_steps(self) -> int:
        return sum(step.status is StepStatus.COMPLETED for step in self.steps)

    @property
    def progress(self) -> float:
        return self.completed_steps / len(self.steps)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        payload = dict(data)
        payload["status"] = TaskStatus(payload.get("status", TaskStatus.PENDING))
        payload["steps"] = [TaskStep.from_dict(step) for step in payload["steps"]]
        return cls(**payload)
