"""Conservative, deterministic planning for explicit Jarvis tasks."""

from __future__ import annotations

import re
import json
from typing import Protocol

from core.tasks.models import Task, TaskStep
from core.tasks.tools import ToolRegistry


class Planner(Protocol):
    def plan(self, goal: str) -> list[TaskStep]: ...


class ChecklistPlanner:
    """Turn an explicit checklist into safe report steps without model guessing."""

    _approval_words = re.compile(
        r"\b(delete|remove|overwrite|send|publish|purchase|buy|install|execute|"
        r"run|launch|upload|post|email|message|modify|write|save|export)\b",
        re.IGNORECASE,
    )

    def plan(self, goal: str) -> list[TaskStep]:
        items = [
            item.strip(" -\t")
            for item in re.split(r"(?:\r?\n|;)+", goal)
            if item.strip(" -\t")
        ]
        if not items:
            raise ValueError("A task goal cannot be empty.")
        return [
            TaskStep(
                title=item,
                tool="report",
                arguments={"message": item},
                requires_approval=bool(self._approval_words.search(item)),
            )
            for item in items
        ]

    def create_task(self, goal: str) -> Task:
        return Task(goal=goal, steps=self.plan(goal))


class IntelligentPlanner:
    """Ask the local model for a tool plan, then strictly validate its output."""

    MAX_STEPS = 12

    def __init__(self, llm, tools: ToolRegistry, fallback: Planner | None = None) -> None:
        self.llm = llm
        self.tools = tools
        self.fallback = fallback or ChecklistPlanner()

    def plan(self, goal: str) -> list[TaskStep]:
        clean_goal = goal.strip()
        if not clean_goal:
            raise ValueError("A task goal cannot be empty.")
        specs = json.dumps(self.tools.public_specs(), ensure_ascii=False)
        prompt = f"""Plan a Jarvis task using only the registered tools below.
Return JSON only: {{"steps":[{{"title":"","tool":"","arguments":{{}}}}]}}

Rules:
- Use only exact registered tool names and declared parameters.
- Create 1 to {self.MAX_STEPS} steps in dependency order.
- Never invent file paths, column names, job descriptions, or missing user input.
- Use report only for a useful final checkpoint, not as a substitute for unavailable work.
- Do not include approval fields; the host enforces approvals.

REGISTERED TOOLS:
{specs}

USER GOAL:
{clean_goal}
"""
        try:
            raw = self.llm.ask(prompt, deep_reasoning=True, response_tokens=900)
            return self._parse(raw)
        except Exception:
            return self.fallback.plan(clean_goal)

    def create_task(self, goal: str) -> Task:
        return Task(goal=goal, steps=self.plan(goal))

    def _parse(self, raw: str) -> list[TaskStep]:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean, flags=re.I)
        data = json.loads(clean)
        items = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(items, list) or not 1 <= len(items) <= self.MAX_STEPS:
            raise ValueError("Planner returned an invalid number of steps.")
        steps = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Planner returned an invalid step.")
            title = str(item.get("title", "")).strip()
            tool = str(item.get("tool", "")).strip()
            arguments = item.get("arguments", {})
            definition = self.tools.definition(tool)
            if not isinstance(arguments, dict):
                raise ValueError("Planner arguments must be an object.")
            unknown = set(arguments) - set(definition.parameters)
            missing = set(definition.required_parameters) - set(arguments)
            if unknown or missing:
                raise ValueError("Planner returned invalid tool arguments.")
            steps.append(
                TaskStep(
                    title=title,
                    tool=tool,
                    arguments=arguments,
                    requires_approval=definition.requires_approval,
                )
            )
        return steps
