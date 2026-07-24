"""Atomic local JSON persistence for Jarvis tasks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from core.tasks.models import Task


class TaskStoreError(RuntimeError):
    """Base error for task persistence failures."""


class TaskNotFoundError(TaskStoreError, LookupError):
    pass


class TaskStoreCorruptionError(TaskStoreError):
    pass


class JsonTaskStore:
    """Persist tasks as one atomically replaced, local JSON document."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()

    def _read_unlocked(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            raise TaskStoreCorruptionError(
                f"Task store could not be read safely: {self.path}"
            ) from exc
        if not isinstance(document, dict):
            raise TaskStoreCorruptionError("Task store root must be a JSON object.")
        if "tasks" in document:
            if document.get("version") != self.SCHEMA_VERSION:
                raise TaskStoreCorruptionError("Unsupported task store version.")
            tasks = document["tasks"]
        else:
            # Read the original Aethon MVP shape for forward migration.
            tasks = document
        if not isinstance(tasks, dict):
            raise TaskStoreCorruptionError("Task store tasks must be a JSON object.")
        return tasks

    def _write_unlocked(self, tasks: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        document = {"version": self.SCHEMA_VERSION, "tasks": tasks}
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(document, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except (OSError, TypeError, ValueError) as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise TaskStoreError(f"Task store could not be written: {self.path}") from exc

    def save(self, task: Task) -> None:
        task.touch()
        with self._lock:
            tasks = self._read_unlocked()
            tasks[task.id] = task.to_dict()
            self._write_unlocked(tasks)

    def get(self, task_id: str) -> Task:
        with self._lock:
            try:
                payload = self._read_unlocked()[task_id]
            except KeyError as exc:
                raise TaskNotFoundError(f"Task not found: {task_id}") from exc
        try:
            return Task.from_dict(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise TaskStoreCorruptionError(
                f"Stored task is invalid: {task_id}"
            ) from exc

    def list(self) -> list[Task]:
        with self._lock:
            payloads = sorted(
                self._read_unlocked().values(),
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )
        try:
            return [Task.from_dict(payload) for payload in payloads]
        except (KeyError, TypeError, ValueError) as exc:
            raise TaskStoreCorruptionError("Stored task data is invalid.") from exc
