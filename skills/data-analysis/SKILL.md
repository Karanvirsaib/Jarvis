---
name: data-analysis
description: Analyze user-provided structured data and produce transparent, reproducible findings and dashboards.
---

# Data analysis

1. Confirm the question, unit of analysis, time range, and relevant definitions before drawing conclusions. Inspect the provided data first and report its row count, fields, missingness, and obvious quality issues.
2. Preserve the source file. Work on a copy and document filters, transformations, exclusions, and assumptions.
3. Prefer simple, reproducible calculations. Check totals, units, duplicates, date ranges, missing values, and outliers. Do not silently impute or discard records.
4. Separate descriptive results from causal claims. State uncertainty and alternative explanations; do not imply causality from correlation alone.
5. Show the key result with an appropriate table or chart and give enough method detail for someone to reproduce it. Verify any dashboard totals against the source data before reporting completion.
6. Do not transmit private datasets to a cloud model or external service without explicit consent. Remove or mask personal identifiers when they are not needed.
