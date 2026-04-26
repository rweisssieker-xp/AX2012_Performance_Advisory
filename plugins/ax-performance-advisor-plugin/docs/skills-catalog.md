# Skills Catalog

The plugin contains many specialized skills. For everyday operation, use the primary set first and keep the rest as advanced capabilities.

## Primary Skills

- `daily-health-check`
- `ax-performance-analysis`
- `sql-server-query-tuning`
- `blocking-analysis`
- `index-risk-review`
- `autonomous-ops-copilot`
- `management-report-generator`
- `evidence-pack-audit`
- `admin-execution-mode`
- `traceparser-dynamicsperf-analysis`

## Grouping

- SQL Diagnostics: query, wait, index, statistics, TempDB, Query Store, plan analysis.
- AX/AOS Diagnostics: batch, AOS, sessions, X++, Trace Parser, DynamicsPerf.
- AI/KI: evidence chat, autonomous ops, learning, prioritization, explainability.
- Governance: CAB, GxP, approval, release gates, performance debt.
- Execution/Admin: preview-only admin workflows and optional portal/agent operations.
- Reporting/Export: dashboard, Power BI, tickets, executive reports.

Generate a machine-readable catalog:

```powershell
python .\scripts\skill_catalog.py --plugin-root . --output .\out\skill-catalog.json
```
