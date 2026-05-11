# YOLO Wave USP Pack

The YOLO Wave USP Pack adds 20 read-only, evidence-backed differentiators to the AX Performance Advisor Platform tab.

These features are not placeholders. They are calculated from existing AXPA evidence files, generated findings, trend store data, and platform extension outputs. When a source is missing, the feature reports a `needs-*` or readiness status instead of inventing values.

## Included Features

1. AX Fix Feasibility Score
2. Business Calendar Awareness
3. AX Transaction Criticality Model
4. User Experience Correlation
5. AX Customization Hotspot Ranking
6. Data Retention Policy Simulator
7. Query Intent Classifier
8. Operational Playbook Generator
9. AX Release / Hotfix Intelligence
10. Executive Risk-to-Money View
11. AI What Changed Analyst
12. AI Batch Negotiator
13. AI Evidence Lawyer
14. AI Remediation Sequencer
15. AI False Positive Reducer
16. AX Performance Debt Register
17. Performance Contract Tests
18. Environment Readiness Score
19. Safe Admin Execution Cockpit
20. AX Survival Horizon

## Output

The pack is written to:

```text
out/<environment>-platform/platform-extensions.json
```

under:

```json
"yoloWaveUspPack": { ... }
```

The dashboard renders it in the Platform tab as:

```text
YOLO Wave USP Pack - 20 neue reale Features
```

## Data Sources

The pack uses these sources when available:

- `sql_top_queries.csv`
- `sql_wait_stats_delta.csv`
- `query_store_runtime.csv`
- `plan_xml_inventory.csv`
- `deadlocks.csv`
- `batch_tasks.csv`
- `batch_jobs.csv`
- `user_sessions.csv`
- `ax_live_blocking.csv`
- `statistics_age.csv`
- `source_status.csv`
- `metadata.json`
- trend SQLite database
- generated AXPA findings

## Safety

All features are read-only. The Safe Admin Execution Cockpit only renders gated review actions. It does not execute SQL or AX changes.
