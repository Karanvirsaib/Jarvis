"""Deterministic analysis of local CSV and Excel data."""

from pathlib import Path
import re
import sqlite3
from uuid import uuid4

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xlsm"}


class Dataset:
    def __init__(self, path: Path, frame: pd.DataFrame, sheet: str | None = None) -> None:
        self.path = path
        self.frame = frame
        self.sheet = sheet

    @classmethod
    def load(cls, path: str | Path, sheet: str | None = None) -> "Dataset":
        resolved = Path(path).expanduser().resolve()
        if resolved.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise ValueError("Supported data files are CSV, XLSX, and XLSM.")
        if not resolved.is_file():
            raise FileNotFoundError(f"Data file not found: {resolved}")
        if resolved.suffix.lower() == ".csv":
            frame = pd.read_csv(resolved)
            selected_sheet = None
        else:
            selected_sheet = sheet or cls.sheet_names(resolved)[0]
            frame = pd.read_excel(resolved, sheet_name=selected_sheet)
        frame.columns = [str(column).strip() for column in frame.columns]
        return cls(resolved, frame, selected_sheet)

    @staticmethod
    def sheet_names(path: str | Path) -> list[str]:
        resolved = Path(path).expanduser().resolve()
        if resolved.suffix.lower() not in {".xlsx", ".xlsm"}:
            return []
        with pd.ExcelFile(resolved) as workbook:
            return list(workbook.sheet_names)

    @property
    def columns(self) -> list[str]:
        return list(self.frame.columns)

    def summary(self) -> str:
        location = self.path.name
        if self.sheet:
            location += f" · sheet: {self.sheet}"
        lines = [
            f"Dataset: {location}",
            f"Rows: {len(self.frame):,}",
            f"Columns ({len(self.columns)}): {', '.join(self.columns)}",
        ]
        for column in self.columns:
            series = self.frame[column]
            missing = int(series.isna().sum())
            numeric = pd.to_numeric(series, errors="coerce")
            non_missing = int(series.notna().sum())
            if non_missing and int(numeric.notna().sum()) == non_missing:
                lines.append(
                    f"- {column}: numeric, missing={missing}, min={numeric.min():g}, "
                    f"max={numeric.max():g}, mean={numeric.mean():.2f}"
                )
            else:
                lines.append(
                    f"- {column}: text, missing={missing}, unique={series.nunique(dropna=True):,}"
                )
        return "\n".join(lines)

    def describe(self, column: str) -> str:
        actual = self.column(column)
        series = self.frame[actual]
        numeric = pd.to_numeric(series, errors="coerce")
        missing = int(series.isna().sum())
        if numeric.notna().any() and numeric.notna().sum() == series.notna().sum():
            return "\n".join(
                [
                    f"Column: {actual}",
                    f"Count: {numeric.count():,}; missing: {missing:,}",
                    f"Min: {numeric.min():g}; max: {numeric.max():g}",
                    f"Mean: {numeric.mean():.2f}; median: {numeric.median():g}",
                    f"Standard deviation: {numeric.std():.2f}",
                ]
            )
        counts = series.dropna().astype(str).value_counts().head(10)
        top = ", ".join(f"{value} ({count})" for value, count in counts.items()) or "none"
        return f"Column: {actual}\nMissing: {missing:,}\nUnique: {series.nunique(dropna=True):,}\nTop values: {top}"

    def grouped(self, value: str, group: str, operation: str) -> pd.Series:
        value_column = self.column(value)
        group_column = self.column(group)
        working = self.frame[[group_column, value_column]].copy()
        working[value_column] = pd.to_numeric(working[value_column], errors="coerce")
        if operation == "count":
            result = working.groupby(group_column, dropna=False)[value_column].count()
        elif operation == "average":
            result = working.groupby(group_column, dropna=False)[value_column].mean()
        else:
            result = working.groupby(group_column, dropna=False)[value_column].sum(min_count=1)
        return result.dropna().sort_values(ascending=False)

    def correlations(self) -> str:
        numeric = self.frame.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
        if numeric.shape[1] < 2:
            return "At least two numeric columns are required for correlations."
        matrix = numeric.corr()
        pairs: list[tuple[float, str, str]] = []
        for index, first in enumerate(matrix.columns):
            for second in matrix.columns[index + 1 :]:
                value = matrix.loc[first, second]
                if pd.notna(value):
                    pairs.append((abs(float(value)), first, second))
        pairs.sort(reverse=True)
        if not pairs:
            return "No usable correlations were found."
        lines = ["Strongest numeric correlations:"]
        for _, first, second in pairs[:10]:
            lines.append(f"- {first} ↔ {second}: {matrix.loc[first, second]:.3f}")
        return "\n".join(lines)

    def column(self, requested: str) -> str:
        lookup = {column.casefold(): column for column in self.columns}
        try:
            return lookup[requested.strip().casefold()]
        except KeyError as exc:
            raise ValueError(
                f"Unknown column '{requested}'. Available: {', '.join(self.columns)}"
            ) from exc


class DataAnalyst:
    def __init__(self, output_directory: str | Path = "output/charts") -> None:
        self.dataset: Dataset | None = None
        self.output_directory = Path(output_directory)
        self.last_chart: Path | None = None

    def handle(self, command: str) -> str | None:
        clean = command.strip()
        lowered = clean.casefold()
        if lowered.startswith("analyze ") or lowered.startswith("load data "):
            prefix = "load data " if lowered.startswith("load data ") else "analyze "
            path = clean[len(prefix) :].strip().strip('"')
            self.dataset = Dataset.load(path)
            self.last_chart = None
            return self.dataset.summary()
        if lowered in {"data summary", "summarize data", "describe data"}:
            return self._required().summary()
        if lowered.startswith("describe column "):
            return self._required().describe(clean[len("describe column ") :])
        if lowered in {"list sheets", "show sheets"}:
            dataset = self._required()
            sheets = Dataset.sheet_names(dataset.path)
            return "Sheets: " + ", ".join(sheets) if sheets else "This is not an Excel workbook."
        if lowered.startswith("use sheet "):
            dataset = self._required()
            sheet = clean[len("use sheet ") :].strip().strip('"')
            self.dataset = Dataset.load(dataset.path, sheet)
            return self.dataset.summary()
        if lowered in {"correlations", "show correlations"}:
            return self._required().correlations()
        if lowered.startswith("sql "):
            return self.run_sql(clean[len("sql ") :])

        grouped = re.fullmatch(r"(sum|average|count|compare) (.+?) by (.+)", clean, re.IGNORECASE)
        if grouped:
            operation, value, group = grouped.groups()
            operation = "sum" if operation.casefold() == "compare" else operation.casefold()
            result = self._required().grouped(value, group, operation)
            return self._format_grouped(result, operation, value, group)

        chart = re.fullmatch(
            r"(?:create |make )?(bar|line|pie)?\s*chart (?:of )?(.+?) by (.+)",
            clean,
            re.IGNORECASE,
        )
        if chart:
            chart_type, value, group = chart.groups()
            return self._chart(value, group, (chart_type or "bar").casefold())
        if lowered in {"data help", "analysis help"}:
            return (
                "Data commands:\n"
                "- analyze <file.csv|file.xlsx>\n"
                "- list sheets / use sheet <name>\n"
                "- data summary / describe column <name>\n"
                "- sum|average|count <value> by <group>\n"
                "- bar|line|pie chart <value> by <group>\n"
                "- correlations"
                "\n- sql SELECT ... FROM data"
            )
        return None

    def run_sql(self, query: str, row_limit: int = 200) -> str:
        dataset = self._required()
        clean = query.strip().rstrip(";").strip()
        first_word = re.match(r"^(?:--[^\n]*\n|/\*.*?\*/\s*)*([a-z]+)", clean, re.I | re.S)
        if not first_word or first_word.group(1).casefold() not in {"select", "with"}:
            raise ValueError("Only read-only SELECT or WITH queries are allowed.")
        with sqlite3.connect(":memory:") as connection:
            dataset.frame.to_sql("data", connection, index=False, if_exists="replace")
            connection.execute("PRAGMA query_only = ON")
            connection.set_authorizer(self._sql_authorizer)
            try:
                result = pd.read_sql_query(
                    f"SELECT * FROM ({clean}) AS jarvis_result LIMIT {int(row_limit)}",
                    connection,
                )
            except (sqlite3.Error, pd.errors.DatabaseError) as exc:
                raise ValueError(f"SQL query failed: {exc}") from exc
        if result.empty:
            return "Query completed successfully with no rows."
        heading = f"SQL result: {len(result):,} row(s)"
        if len(result) == row_limit:
            heading += f" (limited to {row_limit})"
        return f"{heading}\n{result.to_string(index=False)}"

    @staticmethod
    def _sql_authorizer(action: int, _arg1: str, _arg2: str, _database: str, _source: str) -> int:
        denied = {
            sqlite3.SQLITE_INSERT,
            sqlite3.SQLITE_UPDATE,
            sqlite3.SQLITE_DELETE,
            sqlite3.SQLITE_CREATE_INDEX,
            sqlite3.SQLITE_CREATE_TABLE,
            sqlite3.SQLITE_CREATE_TEMP_INDEX,
            sqlite3.SQLITE_CREATE_TEMP_TABLE,
            sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
            sqlite3.SQLITE_CREATE_TEMP_VIEW,
            sqlite3.SQLITE_CREATE_TRIGGER,
            sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_DROP_INDEX,
            sqlite3.SQLITE_DROP_TABLE,
            sqlite3.SQLITE_DROP_TEMP_INDEX,
            sqlite3.SQLITE_DROP_TEMP_TABLE,
            sqlite3.SQLITE_DROP_TEMP_TRIGGER,
            sqlite3.SQLITE_DROP_TEMP_VIEW,
            sqlite3.SQLITE_DROP_TRIGGER,
            sqlite3.SQLITE_DROP_VIEW,
            sqlite3.SQLITE_ALTER_TABLE,
            sqlite3.SQLITE_ATTACH,
            sqlite3.SQLITE_DETACH,
        }
        return sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK

    def _chart(self, value: str, group: str, chart_type: str) -> str:
        result = self._required().grouped(value, group, "sum")
        if result.empty:
            raise ValueError("No numeric data is available for that chart.")
        self.output_directory.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-z0-9]+", "-", f"{value}-by-{group}".casefold()).strip("-")
        path = (self.output_directory / f"{safe_name}-{uuid4().hex[:8]}.png").resolve()
        figure, axis = plt.subplots(figsize=(9, 5.5))
        if chart_type == "pie":
            result.plot(kind="pie", ax=axis, autopct="%1.1f%%", ylabel="")
        else:
            result.sort_index().plot(kind=chart_type, ax=axis, color="#0096C7")
            axis.set_ylabel(value)
            axis.set_xlabel(group)
        axis.set_title(f"{value} by {group}")
        figure.tight_layout()
        figure.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(figure)
        self.last_chart = path
        return f"Created {chart_type} chart: {path}"

    @staticmethod
    def _format_grouped(result: pd.Series, operation: str, value: str, group: str) -> str:
        lines = [f"{operation.title()} of {value} by {group}:"]
        lines.extend(f"- {label}: {amount:,.2f}" for label, amount in result.items())
        return "\n".join(lines) if len(lines) > 1 else "No matching data was found."

    def _required(self) -> Dataset:
        if self.dataset is None:
            raise ValueError("Load data first with: analyze <file.csv|file.xlsx>")
        return self.dataset


CsvDataset = Dataset
