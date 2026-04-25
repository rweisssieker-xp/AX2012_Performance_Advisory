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

## Run

```powershell
python .\scripts\advanced_usps.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\advanced-usps.json
```

The dashboard embeds these results in the `Advanced USPs` tab.
