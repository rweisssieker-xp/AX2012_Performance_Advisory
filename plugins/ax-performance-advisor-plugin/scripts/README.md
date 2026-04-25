# Scripts

This folder is reserved for collectors and report generators.

Planned scripts:

- `mcp_server.py`: read-only MCP server exposing collector and analysis tools.
- `collect_sql_snapshot.ps1`: SQL Server 2016 DMV snapshot collector.
- `collect_ax_events.ps1`: AOS event log and performance counter collector.
- `import_trace_parser_export.py`: Trace Parser export normalizer.
- `generate_report.py`: Markdown/HTML report generator.
- `compare_baseline.py`: before/after comparator for deployments, tuning actions, and batch schedule changes.
- `export_evidence_pack.py`: bundles raw evidence, findings, approvals, and validation results for audit or change management.
- `export_powerbi_dataset.py`: creates dashboard-ready datasets for executive reporting.

Collectors should default to read-only behavior and write timestamped evidence bundles for auditability.

## Evidence Bundle Layout

Recommended output layout:

- `metadata.json`: environment, time window, collector version, analysis version, and source hashes.
- `sql/`: DMV snapshots, wait deltas, plans, blocking chains, deadlocks, file latency, TempDB, Query Store exports.
- `ax/`: batch history, AOS counters, event logs, user sessions, Trace Parser exports, DynamicsPerf extracts.
- `calendar/`: business windows, maintenance windows, deployments, and known operational events.
- `findings/`: normalized findings with severity, confidence, change-readiness score, status, and validation state.
- `reports/`: technical report, management summary, and dashboard extracts.
