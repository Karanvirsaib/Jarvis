"""Confirmed, allowlisted actions for Jarvis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Callable
from uuid import uuid4

from core.memory import MemoryManager


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    title: str
    description: str
    command: tuple[str, ...]
    risk: str = "low"
    launch_mode: str = "process"


@dataclass(frozen=True)
class PendingAction:
    id: str
    definition: ActionDefinition
    requested_at: str


@dataclass(frozen=True)
class AppCandidate:
    name: str
    target: str
    source: str
    score: float


class ApplicationResolver:
    """Resolve installed Windows applications without scanning arbitrary user files."""

    def __init__(self, start_menu_roots: tuple[Path, ...] | None = None) -> None:
        self.start_menu_roots = start_menu_roots or self._default_start_menu_roots()

    def resolve(self, query: str) -> AppCandidate | None:
        normalized = self._normalize(query)
        if not normalized:
            return None
        candidates = self._start_menu_candidates(normalized)
        path_target = shutil.which(query.strip()) or shutil.which(f"{query.strip()}.exe")
        if path_target:
            candidates.append(AppCandidate(Path(path_target).stem, path_target, "PATH", 1.0))
        candidates.extend(self._registered_app_candidates(normalized))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.score, -len(item.name)), reverse=True)
        best = candidates[0]
        if best.score < 0.72:
            return None
        if len(candidates) > 1 and best.score < 0.94 and best.score - candidates[1].score < 0.08:
            names = ", ".join(dict.fromkeys(item.name for item in candidates[:3]))
            raise ValueError(f"That app name is ambiguous. Try a more specific name: {names}.")
        return best

    def _start_menu_candidates(self, query: str) -> list[AppCandidate]:
        candidates: list[AppCandidate] = []
        for root in self.start_menu_roots:
            if not root.exists():
                continue
            try:
                shortcuts = root.rglob("*.lnk")
                for shortcut in shortcuts:
                    name = shortcut.stem
                    score = self._score(query, self._normalize(name))
                    if score >= 0.55:
                        candidates.append(AppCandidate(name, str(shortcut), "Start Menu", score))
            except OSError:
                continue
        return candidates

    @staticmethod
    def _registered_app_candidates(query: str) -> list[AppCandidate]:
        try:
            import winreg
        except ImportError:
            return []
        candidates: list[AppCandidate] = []
        roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
        registry_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        for root in roots:
            try:
                with winreg.OpenKey(root, registry_path) as key:
                    for index in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, index)
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                target = str(winreg.QueryValue(subkey, None))
                        except OSError:
                            continue
                        name = Path(subkey_name).stem
                        score = ApplicationResolver._score(query, ApplicationResolver._normalize(name))
                        if score >= 0.55 and target:
                            candidates.append(AppCandidate(name, target, "Windows registry", score))
            except OSError:
                continue
        return candidates

    @staticmethod
    def _default_start_menu_roots() -> tuple[Path, ...]:
        roots = []
        for variable in ("APPDATA", "PROGRAMDATA"):
            base = os.getenv(variable)
            if base:
                roots.append(Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
        return tuple(roots)

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold().replace(".exe", "")))

    @staticmethod
    def _score(query: str, candidate: str) -> float:
        if query == candidate:
            return 1.0
        if candidate.startswith(query) or query.startswith(candidate):
            return 0.94
        query_tokens, candidate_tokens = set(query.split()), set(candidate.split())
        token_score = len(query_tokens & candidate_tokens) / max(1, len(query_tokens | candidate_tokens))
        return max(SequenceMatcher(None, query, candidate).ratio(), token_score)


class ActionManager:
    """Stages actions and executes only the exact staged allowlisted definition."""

    DEFINITIONS = {
        "calculator": ActionDefinition(
            "calculator", "Open Calculator", "Launch the Windows Calculator application.", ("calc.exe",)
        ),
        "notepad": ActionDefinition(
            "notepad", "Open Notepad", "Launch the Windows Notepad application.", ("notepad.exe",)
        ),
        "file_explorer": ActionDefinition(
            "file_explorer", "Open File Explorer", "Launch Windows File Explorer.", ("explorer.exe",)
        ),
        "calendar": ActionDefinition(
            "calendar", "Open Calendar", "Open the default Windows calendar application.", ("outlookcal:",), launch_mode="shell"
        ),
    }

    def __init__(
        self,
        memory: MemoryManager,
        launcher: Callable[[tuple[str, ...]], None] | None = None,
    ) -> None:
        self.memory = memory
        self._launcher = launcher or self._launch
        self.resolver = ApplicationResolver()
        self.pending: PendingAction | None = None

    def request(self, name: str) -> str:
        definition = self.DEFINITIONS.get(name)
        if definition is None:
            raise ValueError("That action is not in the Jarvis allowlist.")
        if self.pending is not None:
            self.cancel("replaced")
        action = PendingAction(
            id=uuid4().hex[:12],
            definition=definition,
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        self.pending = action
        self.memory.record_action(
            action.id, definition.name, definition.description, "pending", definition.risk
        )
        return self.preview()

    def execute(self, name: str) -> str:
        """Immediately execute a predefined low-risk action and retain its audit trail."""
        self.request(name)
        return self.confirm(self.pending.id if self.pending else None)

    def request_application(self, query: str) -> str:
        candidate = self.resolver.resolve(query)
        if candidate is None:
            return (
                f"I couldn't find an installed application matching '{query}'. "
                "Nothing was run. Try the app's full Start Menu name."
            )
        safe_name = re.sub(r"[^a-z0-9]+", "_", candidate.name.casefold()).strip("_")
        definition = ActionDefinition(
            name=f"application_{safe_name}",
            title=f"Open {candidate.name}",
            description=f"Launch {candidate.name} found via {candidate.source}.",
            command=(candidate.target,),
            launch_mode="shell",
        )
        if self.pending is not None:
            self.cancel("replaced")
        action = PendingAction(uuid4().hex[:12], definition, datetime.now(timezone.utc).isoformat())
        self.pending = action
        self.memory.record_action(action.id, definition.name, definition.description, "pending", definition.risk)
        return self.preview()

    def execute_application(self, query: str) -> str:
        """Resolve and immediately launch an installed app, recording the outcome."""
        result = self.request_application(query)
        if self.pending is None:
            return result
        return self.confirm(self.pending.id)

    def preview(self) -> str:
        if self.pending is None:
            return "There is no action waiting for confirmation."
        action = self.pending
        return (
            "ACTION PREVIEW\n"
            f"{action.definition.title}\n"
            f"{action.definition.description}\n"
            f"Risk: {action.definition.risk.title()}\n"
            f"Action ID: {action.id}\n\n"
            "Nothing has run yet. Choose Confirm or Cancel."
        )

    def confirm(self, action_id: str | None = None) -> str:
        action = self.pending
        if action is None:
            return "There is no action waiting for confirmation."
        if action_id and action_id.strip() != action.id:
            return "That confirmation does not match the pending action. Nothing was run."
        try:
            self._launcher(action.definition.command, action.definition.launch_mode)
        except Exception as exc:
            self.memory.update_action(action.id, "failed", str(exc))
            self.pending = None
            return f"The action failed safely: {exc}"
        self.memory.update_action(action.id, "completed")
        self.pending = None
        return f"Completed: {action.definition.title}."

    def cancel(self, reason: str = "user cancelled") -> str:
        action = self.pending
        if action is None:
            return "There is no action waiting for confirmation."
        self.memory.update_action(action.id, "cancelled", reason)
        self.pending = None
        return f"Cancelled: {action.definition.title}. Nothing was run."

    def status(self) -> dict[str, str] | None:
        if self.pending is None:
            return None
        return {
            "id": self.pending.id,
            "title": self.pending.definition.title,
            "description": self.pending.definition.description,
            "risk": self.pending.definition.risk,
        }

    @staticmethod
    def _launch(command: tuple[str, ...], launch_mode: str = "process") -> None:
        if launch_mode == "shell":
            os.startfile(command[0])
            return
        subprocess.Popen(command, shell=False)
