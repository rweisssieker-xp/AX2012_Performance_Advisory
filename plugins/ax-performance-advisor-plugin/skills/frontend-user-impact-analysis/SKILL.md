---
name: frontend-user-impact-analysis
description: Analyze slow AX frontends, problematic users/clients, broad inventory queries, and machine-wide impact without installing client parsers.
---

# Frontend/User Impact Analysis

Use this skill when AX feels slow for users, a client action appears to slow the whole environment, or an operator needs to identify which user/client/query caused pressure without installing Trace Parser or client-side tooling.

## Inputs

- Local evidence directory only.
- Preferred sources:
  - `ax_live_blocking.csv`
  - `user_sessions.csv`
  - `sql_top_queries.csv`
  - `batch_tasks.csv`
- Optional sources:
  - `query_store_runtime.csv`
  - `trace_parser.csv`
  - `dynamicsperf.csv`

## Command

```powershell
python scripts/frontend_user_usps.py --evidence evidence\<run> --output out\<run>\frontend-user-usp-pack.json
python scripts/generate_dashboard.py --evidence evidence\<run> --output out\<run>\<run>-dashboard.html
```

## What It Produces

The analysis writes 20 concrete frontend/user features:

- AX User Friction Index
- Frontend Blast Radius Radar
- AX Form-to-SQL Attribution
- Misuse Pattern Detection
- Client Host Reputation Score
- Business Process Heatmap
- AX Performance Guardrails
- Smart User Coaching Pack
- AOS Drain Recommendation
- Critical Table Stress Index
- Read Amplification Detector
- Filter Quality Advisor
- Do-Not-Run-Together Matrix
- Incident Fingerprint Library
- AI Evidence-First Troubleshooter
- AX Slow Morning Detector
- SQL-to-AX Table Semantic Explainer
- Change Freeze Risk Advisor
- Executive Business Loss Estimator
- AX Modernization Pressure Index

## Safety

This skill is read-only. It must only analyze local evidence files and write local output files. Do not write to the queried AX or SQL database.
