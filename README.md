# AX Performance Advisor Plugin

Read-only Codex/MCP plugin for Dynamics AX 2012 R3 CU13 and SQL Server 2016 performance analysis.

The plugin collects SQL Server, AX batch, AOS, Trace Parser, DynamicsPerf, event log, and evidence-export data, correlates it with AX table/process knowledge, and generates prioritized, explainable optimization recommendations.

## Repository Layout

- `plugins/ax-performance-advisor-plugin/`: Codex plugin package.
- `plugins/ax-performance-advisor-plugin/scripts/`: collectors, analyzers, exporters, reports, governance tools.
- `plugins/ax-performance-advisor-plugin/skills/`: Codex skill surface.
- `plugins/ax-performance-advisor-plugin/rules/`: rule files for wait stats, AX tables, index risk, batch collisions, severity.
- `plugins/ax-performance-advisor-plugin/sample/evidence/`: anonymized sample evidence for tests and demos.

## Quick Start

```powershell
cd plugins/ax-performance-advisor-plugin
python scripts/analyze_evidence.py --evidence sample/evidence --output out/findings.json
python scripts/generate_report.py --evidence sample/evidence --output out/report.md
python scripts/generate_dashboard.py --evidence sample/evidence --output out/dashboard.html
python -m unittest discover -s tests -v
```

## Safety

- Collectors are read-only by design.
- No automatic AX or SQL changes are executed.
- Live evidence may contain sensitive operational metadata; `evidence/` and `out/` are ignored.
- Use `scripts/mask_evidence.py` before sharing evidence outside the operations boundary.

