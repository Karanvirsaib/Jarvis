"""Local natural-language interpretation for Jarvis tools."""

from dataclasses import dataclass
import json
import re

from core.llm import LLMClient


@dataclass
class Intent:
    action: str = "chat"
    value: str = ""
    group: str = ""
    operation: str = "sum"
    chart_type: str = "bar"
    request: str = ""
    confidence: float = 0.0


class IntentInterpreter:
    ACTIONS = {
        "chat",
        "data_summary",
        "describe_column",
        "grouped_analysis",
        "chart",
        "correlations",
        "generate_python",
        "generate_sql",
    }

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def interpret(self, text: str, columns: list[str] | None = None) -> Intent:
        available = ", ".join(columns or []) or "no dataset loaded"
        prompt = f"""Translate the user's informal or misspelled request into one Jarvis action.
Available dataset columns: {available}

Actions: chat, data_summary, describe_column, grouped_analysis, chart,
correlations, generate_python, generate_sql.

Return ONLY a JSON object with these fields:
action, value, group, operation, chart_type, request, confidence.
operation must be sum, average, or count. chart_type must be bar, line, or pie.
Use exact available column names when the intended column is reasonably clear.
Use chat when the request is not for data analysis or code generation.
Do not invent a missing column. Confidence is a number from 0 to 1.

Examples:
"show me da money by place" -> grouped_analysis, value=revenue, group=region, operation=sum
"make a grapf of sales for each product" -> chart, value=sales, group=product, chart_type=bar
"rite python to clean this csv" -> generate_python

User request: {text}
"""
        response = self.llm.ask(prompt)
        data = self._parse_json(response)
        action = str(data.get("action", "chat"))
        if action not in self.ACTIONS:
            action = "chat"
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        return Intent(
            action=action,
            value=str(data.get("value", "")).strip(),
            group=str(data.get("group", "")).strip(),
            operation=str(data.get("operation", "sum")).strip().lower(),
            chart_type=str(data.get("chart_type", "bar")).strip().lower(),
            request=str(data.get("request", text)).strip() or text,
            confidence=confidence,
        )

    @staticmethod
    def _parse_json(response: str) -> dict[str, object]:
        clean = response.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean, flags=re.I)
        try:
            value = json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, flags=re.S)
            if not match:
                return {}
            try:
                value = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        return value if isinstance(value, dict) else {}
