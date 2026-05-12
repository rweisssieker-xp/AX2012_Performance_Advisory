# Frontend/User USP Pack

The Frontend/User USP Pack turns local AX and SQL evidence into concrete answers for slow AX clients and machine-wide slowdowns caused by broad user actions.

The pack is designed for read-only operation. It does not write to AX or SQL Server. It reads local evidence files and writes local JSON/dashboard output.

## Why It Exists

Classic database monitoring can show expensive SQL, but it usually does not answer:

- Which user or client caused the pressure?
- Which AX form or business process is likely involved?
- Did one broad inventory query slow down the whole machine?
- Which users were affected?
- What should the operator ask or do next?

## Evidence Sources

Preferred local files:

- `ax_live_blocking.csv`
- `user_sessions.csv`
- `sql_top_queries.csv`
- `batch_tasks.csv`

Optional local files:

- `query_store_runtime.csv`
- `trace_parser.csv`
- `dynamicsperf.csv`

## Output

Run:

```powershell
python scripts/frontend_user_usps.py --evidence evidence\<run> --output out\<run>\frontend-user-usp-pack.json
```

The standard platform pipeline also includes this output automatically under:

```text
out\<run>\platform-extensions\frontend-user-usp-pack.json
```

The dashboard shows it in the Platform area as:

```text
Frontend/User USP Pack - 20 konkrete Analysen
```

## The 20 Features

1. AX User Friction Index: ranks users by blocking, reads, elapsed time, session pressure, and wide inventory signals.
2. Frontend Blast Radius Radar: shows broad frontend actions that can slow multiple users or the whole AOS/SQL path.
3. AX Form-to-SQL Attribution: maps query/table signatures to likely AX forms such as `InventOnHand`, `CustTrans`, or ledger forms.
4. Misuse Pattern Detection: detects broad inventory queries and high-read queries with weak filters.
5. Client Host Reputation Score: ranks client/host machines by repeated pressure and blocking signals.
6. Business Process Heatmap: groups frontend pressure by AX business process.
7. AX Performance Guardrails: generates concrete operating rules for users and operators.
8. Smart User Coaching Pack: creates user-specific coaching text from the evidence.
9. AOS Drain Recommendation: flags AOS/host candidates for isolation or peak-window review.
10. Critical Table Stress Index: ranks AX tables by frontend pressure and risk.
11. Read Amplification Detector: finds queries with high reads per execution.
12. Filter Quality Advisor: checks whether queries use expected AX filters.
13. Do-Not-Run-Together Matrix: proposes workload combinations that should be separated.
14. Incident Fingerprint Library: flags known incident patterns, such as inventory availability storms.
15. AI Evidence-First Troubleshooter: tells the operator what proof to collect first.
16. AX Slow Morning Detector: surfaces morning-hour concentration of slow frontend events.
17. SQL-to-AX Table Semantic Explainer: translates table pressure into business-language context.
18. Change Freeze Risk Advisor: warns when fixes should avoid month-end, inventory, audit, or production peaks.
19. Executive Business Loss Estimator: estimates lost minutes and a low/high cost band.
20. AX Modernization Pressure Index: separates tuning/coaching issues from archive or modernization pressure.

## Interpretation

High-confidence frontend incidents usually have at least two of these signals:

- A visible user/client/session in `ax_live_blocking.csv`.
- Broad `InventSum`/`InventDim` aggregation.
- High logical reads or high elapsed time.
- Weak filter quality.
- Blocking rows in the same time window.
- Repeated pressure from the same client/host.

If the pack reports `insufficient frontend pressure evidence`, collect a lightweight flight recorder snapshot during the next complaint window.
