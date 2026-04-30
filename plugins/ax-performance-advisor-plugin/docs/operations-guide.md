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
