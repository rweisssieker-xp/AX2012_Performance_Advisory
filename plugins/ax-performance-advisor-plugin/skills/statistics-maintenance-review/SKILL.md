---
name: statistics-maintenance-review
description: Analyze stale SQL statistics, modification counters, plan risk, and maintenance-window recommendations for AX workloads.
---

# Statistics Maintenance Review

Use this skill when `statistics_age.csv` or stale-statistics findings are present.

## Workflow

1. Identify high modification ratios.
2. Correlate stale statistics with top queries, Query Store, and plan variance.
3. Recommend targeted statistics validation in an approved window.
4. Measure before/after reads, CPU, duration, and plan stability.

## Related Scripts

- `analyze_evidence.py`
- `generate_validation_scripts.py`
- `optimize_maintenance_window.py`

