---
name: remediation-portfolio-optimizer
description: Compare remediation scenarios and choose high-benefit, low-risk AX performance action portfolios.
---

# Remediation Portfolio Optimizer

Use this skill when multiple possible actions exist.

## Workflow

1. Run `simulate_recommendation_scenarios.py`.
2. Run `optimize_remediation_portfolio.py`.
3. Consider benefit, risk, validation cost, rollback, owner, and change window.
4. Prefer reversible operational changes before invasive schema/code changes.

