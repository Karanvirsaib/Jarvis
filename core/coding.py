"""Local Ollama-backed Python and SQL code generation."""

import re

from core.llm import LLMClient


class LocalCoder:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate_python(self, request: str) -> str:
        prompt = f"""Write Python code for the following request.
Return only complete, runnable Python source code. Do not use Markdown fences and
do not include prose before or after the code.
Prefer the standard library unless another package is clearly necessary.
Do not claim to have executed the code.

Request: {request}
"""
        response = self.llm.ask(prompt, deep_reasoning=True)
        return self._python_source(response)

    def generate_sql(self, request: str, columns: list[str] | None = None) -> str:
        schema = ", ".join(columns or []) or "Schema was not provided"
        prompt = f"""Write a read-only SQLite query for the following request.
The loaded table is named data. Its columns are: {schema}.
Return one SQL code block and a short explanation. Never generate INSERT, UPDATE,
DELETE, DROP, ALTER, ATTACH, or other data-changing statements.

Request: {request}
"""
        return self.llm.ask(prompt, deep_reasoning=True)

    @staticmethod
    def _python_source(response: str) -> str:
        """Extract executable Python when a model ignores the no-Markdown rule."""
        match = re.search(r"```(?:python|py)?\s*(.*?)```", response, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return re.sub(r"^```(?:python|py)?\s*|\s*```$", "", response.strip(), flags=re.IGNORECASE).strip()
