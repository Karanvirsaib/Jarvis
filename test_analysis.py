import tempfile
import unittest
from pathlib import Path

from core.analysis import CsvDataset, DataAnalyst


class CsvAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "sales.csv"
        self.csv_path.write_text(
            "region,revenue\nNorth,100\nSouth,200\nNorth,\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_summary_profiles_columns(self) -> None:
        summary = CsvDataset.load(self.csv_path).summary()
        self.assertIn("Rows: 3", summary)
        self.assertIn("revenue: numeric, missing=1", summary)

    def test_command_router_loads_data(self) -> None:
        analyst = DataAnalyst()
        result = analyst.handle(f'analyze "{self.csv_path}"')
        self.assertIn("sales.csv", result or "")
        self.assertIn("Mean: 150.00", analyst.handle("describe column revenue") or "")

    def test_grouped_analysis(self) -> None:
        analyst = DataAnalyst()
        analyst.handle(f'analyze "{self.csv_path}"')
        result = analyst.handle("sum revenue by region")
        self.assertIn("North: 100.00", result or "")
        self.assertIn("South: 200.00", result or "")

    def test_excel_sheet_and_chart(self) -> None:
        workbook = Path(self.temp_dir.name) / "sales.xlsx"
        import pandas as pd

        with pd.ExcelWriter(workbook) as writer:
            pd.DataFrame(
                {"region": ["North", "South"], "revenue": [100, 200]}
            ).to_excel(writer, sheet_name="Sales", index=False)
            pd.DataFrame({"item": ["A"], "stock": [5]}).to_excel(
                writer, sheet_name="Inventory", index=False
            )
        analyst = DataAnalyst(Path(self.temp_dir.name) / "charts")
        loaded = analyst.handle(f'analyze "{workbook}"')
        self.assertIn("sheet: Sales", loaded or "")
        self.assertEqual(analyst.handle("list sheets"), "Sheets: Sales, Inventory")
        chart = analyst.handle("bar chart revenue by region")
        self.assertIn("Created bar chart", chart or "")
        self.assertTrue(analyst.last_chart and analyst.last_chart.is_file())

    def test_read_only_sql_over_loaded_data(self) -> None:
        analyst = DataAnalyst()
        analyst.handle(f'analyze "{self.csv_path}"')
        result = analyst.handle(
            "sql SELECT region, SUM(revenue) AS total FROM data GROUP BY region ORDER BY total DESC"
        )
        self.assertIn("South", result or "")
        self.assertIn("200", result or "")

    def test_sql_common_table_expression(self) -> None:
        analyst = DataAnalyst()
        analyst.handle(f'analyze "{self.csv_path}"')
        result = analyst.handle(
            "sql WITH totals AS (SELECT SUM(revenue) total FROM data) SELECT total FROM totals"
        )
        self.assertIn("300", result or "")

    def test_sql_writes_are_rejected(self) -> None:
        analyst = DataAnalyst()
        analyst.handle(f'analyze "{self.csv_path}"')
        with self.assertRaisesRegex(ValueError, "Only read-only"):
            analyst.run_sql("DELETE FROM data")


if __name__ == "__main__":
    unittest.main()
