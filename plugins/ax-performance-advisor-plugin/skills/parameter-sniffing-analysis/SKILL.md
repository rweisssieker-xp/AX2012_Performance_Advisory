---
name: parameter-sniffing-analysis
description: Analyze plan-cache variance, Query Store runtime variation, and parameter-sensitive AX query candidates.
---

# Parameter Sniffing Analysis

Use this skill when plan count, runtime variance, or Query Store evidence suggests unstable plans.

## Workflow

1. Run `scripts/watch_plan_regressions.py`.
2. Review `plan_cache_variance.csv` and `query_store_runtime.csv`.
3. Compare query family, object, module, and business window.
4. Recommend plan capture and TEST validation before any forcing or code change.

## Related Scripts

- `watch_plan_regressions.py`
- `analyze_query_families.py`
- `parse_plan_xml.py`

