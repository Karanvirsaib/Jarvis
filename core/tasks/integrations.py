"""Adapters that expose existing Jarvis capabilities as task tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.tasks.tools import ToolRegistry, create_default_registry

if TYPE_CHECKING:
    from core.assistant import JarvisAssistant


def create_jarvis_registry(assistant: JarvisAssistant) -> ToolRegistry:
    registry = create_default_registry()

    def load_dataset(path: str, sheet: str | None = None) -> str:
        command = f'analyze "{path}"'
        result = assistant.analyst.handle(command)
        if sheet:
            result = assistant.analyst.handle(f'use sheet "{sheet}"')
        return result or "Dataset loaded."

    def summarize_dataset() -> str:
        return assistant.analyst.handle("data summary") or "Dataset summarized."

    def describe_column(column: str) -> str:
        return assistant.analyst.handle(f"describe column {column}") or ""

    def grouped_analysis(value: str, group: str, operation: str = "sum") -> str:
        normalized = operation.casefold()
        if normalized not in {"sum", "average", "count"}:
            raise ValueError("Operation must be sum, average, or count.")
        return assistant.analyst.handle(f"{normalized} {value} by {group}") or ""

    def create_chart(value: str, group: str, chart_type: str = "bar") -> str:
        normalized = chart_type.casefold()
        if normalized not in {"bar", "line", "pie"}:
            raise ValueError("Chart type must be bar, line, or pie.")
        return assistant.analyst.handle(f"{normalized} chart {value} by {group}") or ""

    def correlations() -> str:
        return assistant.analyst.handle("correlations") or ""

    def run_sql(query: str) -> str:
        return assistant.analyst.run_sql(query)

    def research_web(query: str) -> str:
        return assistant.researcher.research(query)

    def generate_python(request: str) -> str:
        return assistant.coder.generate_python(request)

    def generate_sql(request: str) -> str:
        columns = assistant.analyst.dataset.columns if assistant.analyst.dataset else None
        return assistant.coder.generate_sql(request, columns)

    def load_resume(path: str) -> str:
        return assistant.resume.load(path)

    def tailor_resume(job_description: str) -> str:
        return assistant.resume.tailor(job_description)

    def export_resume(format: str) -> str:
        normalized = format.casefold()
        if normalized not in {"word", "pdf"}:
            raise ValueError("Resume format must be word or pdf.")
        return str(assistant.resume.export(normalized))

    def open_application(name: str) -> str:
        return assistant.actions.execute_application(name)

    definitions = [
        ("load_dataset", load_dataset, False, "Load a local CSV or Excel dataset. Parameters: path, optional sheet."),
        ("summarize_dataset", summarize_dataset, False, "Summarize the currently loaded dataset."),
        ("describe_column", describe_column, False, "Profile one loaded dataset column."),
        ("grouped_analysis", grouped_analysis, False, "Aggregate a value by a group using sum, average, or count."),
        ("create_chart", create_chart, True, "Create and save a bar, line, or pie chart image."),
        ("correlations", correlations, False, "Find correlations in the loaded dataset."),
        ("run_sql", run_sql, False, "Run a read-only SELECT or WITH query against the loaded dataset."),
        ("research_web", research_web, False, "Research a current question using public web evidence."),
        ("generate_python", generate_python, False, "Generate Python source code without executing it."),
        ("generate_sql", generate_sql, False, "Generate a read-only SQL query without executing it."),
        ("load_resume", load_resume, False, "Load a local resume as the factual source."),
        ("tailor_resume", tailor_resume, False, "Create a truth-constrained resume draft for a job description."),
        ("export_resume", export_resume, True, "Write the approved resume draft as Word or PDF."),
        ("open_application", open_application, True, "Launch an installed Windows application."),
    ]
    for name, handler, approval, description in definitions:
        registry.register(
            name,
            handler,
            requires_approval=approval,
            description=description,
        )
    return registry
