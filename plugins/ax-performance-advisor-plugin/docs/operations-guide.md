# Operations Guide

This guide describes a normal read-only AXPA run.

## 1. Prepare

- Use Windows Authentication or a least-privilege SQL login.
- Prefer `VIEW SERVER STATE` for SQL DMV evidence.
- Do not use accounts with `ALTER`, `CREATE INDEX`, `UPDATE`, or `DELETE` for normal analysis.
- Pick a local evidence directory, for example `evidence/prod-2026-04-25`.

## 2. Collect SQL Evidence

```powershell
.\scripts\collect_sql_snapshot.ps1 `
  -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory .\evidence\prod-snapshot `
  -AxDatabaseName AXDB `
  -IncludeQueryStore `
  -IncludeDeadlocks `
  -WaitDeltaSeconds 60
```

## 3. Collect AX Evidence

```powershell
.\scripts\collect_ax_db_snapshot.ps1 `
  -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory .\evidence\prod-snapshot `
  -Days 14
```

## 4. Collect AOS / Event Evidence

```powershell
.\scripts\collect_aos_counters.ps1 `
  -ComputerName AOSSERVER `
  -OutputDirectory .\evidence\prod-snapshot `
  -SampleSeconds 30

.\scripts\collect_ax_events.ps1 `
  -OutputDirectory .\evidence\prod-snapshot `
  -Hours 24
```

Run the event collector on the AOS host if remote event log access is not configured.

## 5. Import Optional Evidence

```powershell
python .\scripts\import_trace_parser_export.py --input .\incoming\trace.csv --output .\evidence\prod-snapshot\trace_parser.csv
python .\scripts\import_dynamicsperf_export.py --input .\incoming\dynamicsperf.csv --output .\evidence\prod-snapshot\dynamicsperf.csv
python .\scripts\parse_deadlock_xml.py --input .\incoming\deadlock.xml --output .\evidence\prod-snapshot\deadlock_processes.csv
python .\scripts\parse_plan_xml.py --input .\incoming\plan.sqlplan --output .\evidence\prod-snapshot\plan_operators.csv
```

## 6. Analyze and Report

Preferred single-command workflow:

```powershell
python .\scripts\run_axpa_pipeline.py `
  --environment prod-snapshot `
  --server SERVER `
  --database AXDB `
  --evidence .\evidence\prod-snapshot `
  --out .\out `
  --collect
```

The pipeline uses a lock file by default at `out/<environment>.lock` to prevent
overlapping scheduled runs. Use `--lock-file` to override the location and
`--stale-lock-minutes` for stale lock recovery.

Manual workflow:

```powershell
python .\scripts\analyze_evidence.py --evidence .\evidence\prod-snapshot --output .\out\findings.json
python .\scripts\generate_report.py --evidence .\evidence\prod-snapshot --output .\out\technical-report.md
python .\scripts\generate_dashboard.py --evidence .\evidence\prod-snapshot --output .\out\dashboard.html
python .\scripts\autonomous_ops.py --evidence .\evidence\prod-snapshot --output .\out\autonomous-ops.json
python .\scripts\update_trend_store.py --evidence .\evidence\prod-snapshot --db .\out\axpa-trends.sqlite
python .\scripts\platform_extensions.py --evidence .\evidence\prod-snapshot --output-dir .\out\prod-platform --trend-db .\out\axpa-trends.sqlite
```

The dashboard includes a real AX Batch Collision Analysis tab when `batch_tasks.csv`
or `batch_jobs.csv` contains start and end timestamps. The analysis calculates:

- overlapping batch task pairs and affected batch groups,
- peak parallelism and the timestamp of the peak,
- short-running batch storms in the same minute,
- long-running batch tasks,
- live blocking rows observed during the same collector run,
- persistent batch collision metrics in the SQLite trend store.

The dashboard also includes a `Platform` tab. It is generated from the same
evidence and adds trend history, recommendation lifecycle, incident replay,
query-plan variance, deadlock graph records, AOS topology, scheduler hardening,
push-readiness, X++ attribution, environment drift checks, and an AI decision
cockpit. External systems are not updated unless separate credentials and
approval policies are configured.

Optional push integrations become push-capable when these environment variables
are configured:

- Power BI: `AXPA_POWERBI_WORKSPACE_ID`, `AXPA_POWERBI_DATASET_ID`, `AXPA_POWERBI_TOKEN`
- Teams: `AXPA_TEAMS_WEBHOOK_URL`
- Azure DevOps: `AXPA_ADO_ORG`, `AXPA_ADO_PROJECT`, `AXPA_ADO_TOKEN`
- Jira: `AXPA_JIRA_BASE_URL`, `AXPA_JIRA_PROJECT`, `AXPA_JIRA_TOKEN`
- ServiceNow: `AXPA_SN_INSTANCE_URL`, `AXPA_SN_TOKEN`

Run productive/dry-run pushes through the audited push hub:

```powershell
python .\scripts\push_integrations.py `
  --evidence .\evidence\prod-snapshot `
  --targets teams,ado,jira,servicenow,powerbi `
  --audit-db .\out\prod-push-audit.sqlite `
  --limit 20 `
  --dry-run
```

Trace Parser, DynamicsPerf, or AX model mapping evidence is required for
high-confidence SQL Query -> X++ class/method attribution. Without those files,
the plugin reports low-confidence attribution and the exact collector to run.

## 7. Share Safely

Before sharing evidence outside the trusted team:

```powershell
python .\scripts\mask_evidence.py --input .\evidence\prod-snapshot --output .\out\masked-evidence
```

Attach reports, masked evidence, validation scripts, and CAB packages only after review.
# Production Readiness Closeout

Use this sequence when moving from local analysis to repeatable operations:

```powershell
python scripts/build_production_readiness_pack.py `
  --environment bras3333 `
  --server Bras3333 `
  --database MicrosoftDynamicsGBLAX `
  --evidence evidence/bras3333-test-20260505 `
  --out out `
  --dashboard out/bras3333-test-20260505-dashboard.html `
  --output out/bras3333-production-readiness-pack.json
```

Then run the local HTTP dashboard QA instead of opening the file through `file://`:

```powershell
python scripts/qa_dashboard_http.py `
  --root . `
  --dashboard out/bras3333-test-20260505-dashboard.html `
  --require "YOLO Wave USP Pack" `
  --require "AX Survival Horizon" `
  --output out/bras3333-dashboard-http-qa.json
```

The readiness pack records concrete commands for:

- Windows Task Scheduler installation.
- Scheduler manifest, task and lock health check.
- Trace Parser / DynamicsPerf / AX model mapping evidence.
- Push configuration preflight without sending data.
- Productive push readiness for Teams, Azure DevOps, Jira, ServiceNow and Power BI.
- Recommendation lifecycle approval gates.
- Admin execution Go/No-Go preflight.
- Dashboard HTTP QA.

AXPA remains read-only by default. Productive push and admin execution require external credentials, explicit approval state and audit evidence.

## Operator Cockpit and Batch Control Tower

The production dashboard now includes an Operator Cockpit and a Batch Control Tower. Both features are generated from local evidence files only. They do not write to the AX or SQL Server database.

Operator Cockpit answers the first operational question:

- What is the top suspect right now?
- Which safe local checks should be done next?
- Which actions must not be executed without CAB or TEST evidence?
- Which proof is missing before an implementation decision?

Batch Control Tower answers the batch-specific question:

- Which hours and batch groups create the highest collision pressure?
- Which batch group should be moved from which current window to which target window?
- Which dependency, SLA, and AOS affinity evidence supports the move?
- Which TEST validation and rollback text belongs to the proposal?

User & Client Impact Radar answers the internal support question:

- Which AX users, client machines and user/client pairs are associated with live blocking, high reads or broad inventory queries?
- Is the row only an active-session context signal, an affected user, a possible blocker, a machine-impact suspect, or both?
- Which sessions, tables, client types and sample queries support the classification?
- Which concrete admin questions should be asked before any operational action?

This view is intentionally internal and unmasked. Use `mask_evidence.py` before sharing reports outside the trusted operations team.

Generate the BRAS3333 dashboard locally:

```powershell
python .\scripts\generate_dashboard.py `
  --evidence .\evidence\bras3333-full-20260511-061558 `
  --output .\out\bras3333-full-20260511-061558\bras3333-full-20260511-061558-dashboard.html
```

Validate that the new sections are present:

```powershell
python .\scripts\qa_dashboard_http.py `
  --root . `
  --dashboard .\out\bras3333-full-20260511-061558\bras3333-full-20260511-061558-dashboard.html `
  --require "Operator Cockpit" `
  --require "Safety Guard" `
  --require "Batch Control Tower" `
  --require "Attribution Engine" `
  --require "Daily Production Loop" `
  --output .\out\dashboard-new-sections-qa.json
```

Safety Guard scans collector scripts and permission evidence for write-risk signals. A green or amber result still means analysis-only; it is not approval for SQL/AX changes. If a write verb appears in a collector script, the dashboard marks the run unsafe until the script is corrected.

Attribution Engine separates:

- observed evidence from SQL, blocking, batch and trace files;
- inferred AX form/process hypotheses;
- missing proof such as Trace Parser, DynamicsPerf or AX model mapping.

Daily Production Loop summarizes local scheduler, dashboard QA, push readiness and next actions. Missing push integrations do not block local read-only diagnostics.

## CEO Cockpit

The CEO Cockpit is a board-level view over the same local evidence. It does not query or write AX/SQL directly. It turns technical findings into decision artifacts:

- CEO Health Score, risk band, business impact estimate in EUR and stability confidence.
- Decision Queue with owner, deadline, business impact, evidence quality and risk if deferred.
- Business Process Heatmap for Finance, Inventory, Sales, Production, Integration and AX Core.
- Risk of Doing Nothing over 7, 30 and 90 days.
- Change Portfolio grouped into Quick Win, Controlled Change, Strategic and Defer/Monitor.
- SLA Breach Forecast for batch groups with late-after-07:00 and peak-hour signals.
- AX Legacy Risk Index and D365/modernization signal.
- Crisis Mode when red risk, live blocking, high batch peak or wide inventory queries are present.
- Board-ready monthly report generated locally as `platform-extensions/ceo-board-report.md`.

The EUR impact is intentionally directional. Replace the default local cost model with real hourly process cost, SLA penalties or order backlog KPIs before using it as a financial forecast.

Useful preflight commands:

```powershell
python scripts/check_scheduler_health.py `
  --manifest out/bras3333-prodready-20260509-pipeline-manifest.json `
  --lock-file out/bras3333.lock `
  --task-name AXPA-bras3333 `
  --output out/bras3333-scheduler-health.json

python scripts/validate_push_readiness.py `
  --targets teams,ado,jira,servicenow,powerbi `
  --audit-db out/bras3333-push-audit.sqlite `
  --output out/bras3333-push-readiness.json

python scripts/admin_gate_preflight.py `
  --evidence evidence/bras3333-test-20260505 `
  --output-dir out/bras3333-admin-execution `
  --environment TEST `
  --output out/bras3333-admin-gate-preflight.json
```
