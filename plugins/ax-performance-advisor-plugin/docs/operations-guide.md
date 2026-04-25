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

```powershell
python .\scripts\analyze_evidence.py --evidence .\evidence\prod-snapshot --output .\out\findings.json
python .\scripts\generate_report.py --evidence .\evidence\prod-snapshot --output .\out\technical-report.md
python .\scripts\generate_dashboard.py --evidence .\evidence\prod-snapshot --output .\out\dashboard.html
python .\scripts\autonomous_ops.py --evidence .\evidence\prod-snapshot --output .\out\autonomous-ops.json
```

## 7. Share Safely

Before sharing evidence outside the trusted team:

```powershell
python .\scripts\mask_evidence.py --input .\evidence\prod-snapshot --output .\out\masked-evidence
```

Attach reports, masked evidence, validation scripts, and CAB packages only after review.
