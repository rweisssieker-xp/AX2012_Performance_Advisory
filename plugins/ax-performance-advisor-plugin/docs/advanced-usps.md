# Advanced USP Pack

The advanced USP pack adds operational features that improve prioritization, governance, and executive decision support.

## Features

- SLO burn-rate checks for playbook-level high-risk budgets.
- Maintenance window sequencing by finding type.
- Cost-of-delay risk points for open findings.
- Release gate decision based on high/critical blockers.
- Retention/archive candidates from data-growth and stale-statistics signals.
- Known-issue matching from `rules/known_issues.json`.
- Executive one-minute briefing, decision ask, and deferred-risk statement.
- Temporal hotspot map from Batch Tasks, AX live blocking, Query Store runtime, and SQL wait deltas.
- Workload fingerprinting for Inventory/Production, Finance, Sales, Purchasing, Integration, Reporting, and General AX.
- Archive impact sandbox for candidate tables with 10%, 25%, and 50% data-reduction scenarios.
- Performance budgeting with pass/fail gates for critical findings, high findings, blocking, and query regressions.
- Validation orchestrator that turns top findings into before/after test steps and acceptance criteria.
- Operator copilot context with evidence files, top findings, and suggested follow-up questions.
- Self-calibrating thresholds from observed Query Store runtime percentiles.

## Run

```powershell
python .\scripts\advanced_usps.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\advanced-usps.json
```

The dashboard embeds these results in the `Advanced USPs` tab.
