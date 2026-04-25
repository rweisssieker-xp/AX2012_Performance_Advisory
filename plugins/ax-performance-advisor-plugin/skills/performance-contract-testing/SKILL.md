---
name: performance-contract-testing
description: Define and evaluate AX performance contracts, budgets, release gates, and generated regression tests.
---

# Performance Contract Testing

Use this skill for deployments and release validation.

## Workflow

1. Run `scripts/generate_performance_contract_tests.py`.
2. Run `scripts/release_gate.py` for before/after evidence.
3. Run `scripts/generate_regression_unit_tests.py` to preserve regressions as future checks.

