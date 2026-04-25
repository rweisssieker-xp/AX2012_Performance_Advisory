# Enterprise Observability Layer

This layer closes the main platform gaps compared with general database observability tools while keeping AX-specific diagnosis as the primary differentiator.

## Features

- SQLite time-series store for AXPA runs, metrics, findings, waits, query families, and module scores.
- Alert generation with severity, route, acknowledge requirement, silence key, evidence, and next action.
- Estate inventory for multiple AX/SQL evidence roots.
- Query/plan repository with query families and plan-regression candidates.
- Notification payload exports for Teams, ServiceNow, and PagerDuty.
- Competitive coverage summary that separates implemented features from external configuration requirements.

## Run

```powershell
python .\scripts\enterprise_observability.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output-dir .\out\enterprise-observability `
  --estate .\evidence\IT-TEST-ERP4CU
```

The dashboard embeds this output in the `Enterprise Observability` tab.

## Boundaries

This layer exports notification payloads but does not call external webhooks unless a deployment-specific integration script is configured with approved credentials.
