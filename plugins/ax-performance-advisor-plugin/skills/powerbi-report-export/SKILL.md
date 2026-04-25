---
name: powerbi-report-export
description: Export AXPA findings and metrics for Power BI CSV datasets or streaming endpoint push when credentials are configured.
---

# Power BI Report Export

Use this skill for dashboard-ready outputs.

## Workflow

1. Run `export_powerbi_dataset.py` for CSV.
2. Use `push_powerbi_dataset.py` only when `POWERBI_PUSH_ENDPOINT` is configured.
3. Include dimensions: module, owner, severity, status, classification, debt, SLA, and trend.

