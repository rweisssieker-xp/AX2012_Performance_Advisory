# AX Performance Advisor Plugin

Read-only Codex/MCP plugin for Dynamics AX 2012 R3 CU13 and SQL Server 2016 performance analysis.

AX Performance Advisor collects SQL Server, AX batch, AOS, Trace Parser, DynamicsPerf, event log, and exported evidence data. It correlates that data with AX table/process knowledge and produces prioritized, explainable recommendations, dashboards, change drafts, validation plans, and governance artifacts.

## What It Does

- SQL Server analysis: top queries, waits, blocking, deadlocks, file latency, TempDB, statistics, missing indexes, plan variance, Query Store.
- Dynamics AX 2012 analysis: batch jobs, sessions, AOS counters, AIF/services, Retail load, Trace Parser, DynamicsPerf, AX SQL trace.
- AX-specific correlation: SQL query pressure to tables, modules, owners, business processes, batch windows, and validation actions.
- AI/KI advisory: evidence-grounded root-cause chat, remediation planning, explainability, autonomous investigation queues, next-best actions, and executive briefings.
- Governance: CAB/GxP-friendly change drafts, audit evidence packs, masked exports, release gates, SLOs, debt registers, and ticket exports.

## Quick Start

Run against anonymized sample evidence:

```powershell
cd plugins/ax-performance-advisor-plugin
python scripts/analyze_evidence.py --evidence sample/evidence --output out/findings.json
python scripts/generate_report.py --evidence sample/evidence --output out/report.md
python scripts/generate_dashboard.py --evidence sample/evidence --output out/dashboard.html
python -m unittest discover -s tests -v
```

Open the generated dashboard:

```text
plugins/ax-performance-advisor-plugin/out/dashboard.html
```

## Live Evidence Example

Collectors are designed to be read-only. Use a least-privilege SQL login or Windows Authentication.

```powershell
cd plugins/ax-performance-advisor-plugin

.\scripts\collect_sql_snapshot.ps1 `
  -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory .\evidence\prod-snapshot `
  -AxDatabaseName AXDB `
  -IncludeQueryStore `
  -IncludeDeadlocks

.\scripts\collect_ax_db_snapshot.ps1 `
  -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory .\evidence\prod-snapshot `
  -Days 14

python .\scripts\generate_dashboard.py `
  --evidence .\evidence\prod-snapshot `
  --output .\out\prod-dashboard.html
```

## Repository Layout

- `plugins/ax-performance-advisor-plugin/`: Codex plugin package.
- `plugins/ax-performance-advisor-plugin/scripts/`: collectors, analyzers, exporters, reports, governance tools.
- `plugins/ax-performance-advisor-plugin/skills/`: Codex skill surface.
- `plugins/ax-performance-advisor-plugin/rules/`: rule files for waits, AX tables, index risk, batch collisions, severity.
- `plugins/ax-performance-advisor-plugin/sample/evidence/`: anonymized sample evidence for tests and demos.
- `plugins/ax-performance-advisor-plugin/docs/`: architecture, operations, security, feature, and release documentation.

## Documentation

Start with [Documentation Index](plugins/ax-performance-advisor-plugin/docs/INDEX.md).

Key documents:

- [Architecture](plugins/ax-performance-advisor-plugin/docs/architecture.md)
- [Operations Guide](plugins/ax-performance-advisor-plugin/docs/operations-guide.md)
- [Testing Guide](plugins/ax-performance-advisor-plugin/docs/testing-guide.md)
- [Security Model](plugins/ax-performance-advisor-plugin/docs/security-model.md)
- [Threat Model](plugins/ax-performance-advisor-plugin/docs/threat-model.md)
- [Release Runbook](plugins/ax-performance-advisor-plugin/docs/release-runbook.md)
- [Autonomous Ops](plugins/ax-performance-advisor-plugin/docs/autonomous-ops.md)

## Safety

- Collectors are read-only by design.
- No automatic AX or SQL changes are executed.
- Admin execution artifacts are preview-only unless a human admin approves and runs them outside the dashboard.
- Live evidence may contain sensitive operational metadata; `evidence/` and `out/` are ignored.
- Use `scripts/mask_evidence.py` before sharing evidence outside the trusted operations boundary.

## Development Checks

```powershell
python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests
python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v
python -m json.tool plugins/ax-performance-advisor-plugin/.codex-plugin/plugin.json
```
