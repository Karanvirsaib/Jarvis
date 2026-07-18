"""Local Ollama-backed Python and SQL code generation."""

from core.llm import LLMClient


class LocalCoder:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def generate_python(self, request: str) -> str:
        prompt = f"""Write Python code for the following request.
Return one complete, runnable code block followed by at most three short usage notes.
Prefer the standard library unless another package is clearly necessary.
Do not claim to have executed the code.

Request: {request}
"""
        return self.llm.ask(prompt, deep_reasoning=True)

    def generate_sql(self, request: str, columns: list[str] | None = None) -> str:
        schema = ", ".join(columns or []) or "Schema was not provided"
        prompt = f"""Write a read-only SQLite query for the following request.
The loaded table is named data. Its columns are: {schema}.
Return one SQL code block and a short explanation. Never generate INSERT, UPDATE,
DELETE, DROP, ALTER, ATTACH, or other data-changing statements.

Request: {request}
"""
        return self.llm.ask(prompt, deep_reasoning=True)
