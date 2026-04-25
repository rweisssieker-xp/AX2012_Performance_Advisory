---
name: environment-drift-analysis
description: Compare AX environments, explain TEST-vs-PROD gaps, produce repro checklist, and summarize fleet risk.
---

# Environment Drift Analysis

Use this skill when performance differs between PROD, TEST, PREPROD, or DR.

## Workflow

1. Run `compare_environment_drift.py`.
2. Run `build_repro_checklist.py`.
3. Run `fleet_view.py` for multiple evidence directories.
4. Identify data volume, stats age, settings, batch schedule, AOS, and maintenance drift.

