---
name: query-store-regression-analysis
description: Analyze Query Store and plan-cache runtime evidence for SQL plan regressions and release-gate decisions.
---

# Query Store Regression Analysis

Use this skill for Query Store, deployment regression, and release gates.

## Workflow

1. Run `watch_plan_regressions.py`.
2. Run `release_gate.py` for before/after evidence.
3. Review plan IDs, duration deltas, reads, CPU, and affected AX tables.
4. Recommend pass/fail, observe, or rollback review.

