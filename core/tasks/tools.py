"""Explicit allowlist of tools available to the Jarvis task runner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import inspect
from typing import Any


Tool = Callable[..., Any]


class UnknownToolError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    handler: Tool
    requires_approval: bool = False
    description: str = ""
    parameters: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()


class ToolRegistry:
    """Allow the task engine to call only host-registered Python functions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        tool: Tool,
        *,
        requires_approval: bool = False,
        description: str = "",
    ) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Tool names cannot be empty.")
        if not callable(tool):
            raise TypeError("Registered tools must be callable.")
        if normalized in self._tools:
            raise ValueError(f"Tool already registered: {normalized}")
        signature = inspect.signature(tool)
        parameters = tuple(
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.kind
            in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
        )
        required = tuple(
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.name in parameters
            and parameter.default is inspect.Parameter.empty
        )
        self._tools[normalized] = ToolDefinition(
            normalized,
            tool,
            requires_approval=requires_approval,
            description=description.strip(),
            parameters=parameters,
            required_parameters=required,
        )

    def definition(self, name: str) -> ToolDefinition:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise UnknownToolError(f"Tool is not registered: {name}") from exc

    def requires_approval(self, name: str) -> bool:
        return self.definition(name).requires_approval

    def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a dictionary.")
        definition = self.definition(name)
        unknown = set(arguments) - set(definition.parameters)
        missing = set(definition.required_parameters) - set(arguments)
        if unknown:
            raise ValueError(f"Unknown arguments for {name}: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"Missing arguments for {name}: {', '.join(sorted(missing))}")
        return definition.handler(**arguments)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def public_specs(self) -> list[dict[str, Any]]:
        return [
            {
                "name": definition.name,
                "description": definition.description,
                "parameters": list(definition.parameters),
                "required": list(definition.required_parameters),
                "requires_approval": definition.requires_approval,
            }
            for definition in sorted(self._tools.values(), key=lambda item: item.name)
        ]


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        "report",
        lambda message: message,
        description="Record a textual checkpoint or conclusion.",
    )
    return registry
