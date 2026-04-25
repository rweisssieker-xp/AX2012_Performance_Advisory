# Architecture

AX Performance Advisor is a local, read-only Codex/MCP plugin for Dynamics AX 2012 R3 CU13 and SQL Server 2016 performance diagnostics.

## Components

- **Collectors** read operational data from SQL Server, AX database tables, AOS counters, Windows events, Trace Parser exports, DynamicsPerf exports, deadlock XML, and execution-plan XML.
- **Evidence bundle** stores normalized CSV/JSON files under a local evidence directory.
- **Analysis core** loads evidence, applies AX-aware rules, and emits normalized findings.
- **Advisory packs** generate AI/KI, autonomous ops, governance, strategy, market, learning, and enterprise observability outputs.
- **Reports and dashboard** render Markdown, HTML, JSON, CSV, Power BI-ready data, tickets, CAB packages, and release artifacts.
- **Skills and MCP server** expose repeatable workflows to Codex and compatible clients.

## Data Flow

```text
SQL / AX / AOS / Exports
  -> read-only collectors or importers
  -> evidence bundle
  -> analyze_evidence()
  -> normalized findings
  -> advisory packs
  -> reports, dashboard, tickets, CAB, validation, Power BI
```

## Trust Boundaries

- The repository should not contain live evidence, credentials, customer data, or generated reports from customer systems.
- `evidence/` and `out/` are local operational workspaces and are ignored by Git.
- Admin execution artifacts are generated as guarded previews. They are not run by the dashboard.
- External integrations such as Azure DevOps, Jira, Power BI, notifications, and LLM connectors require explicit configuration.

## Extension Points

- Add new collector scripts under `scripts/`.
- Add new analyzer logic to `axpa_core.py` or a focused advisory pack.
- Add skills under `skills/<name>/SKILL.md`.
- Add rules under `rules/`.
- Add tests under `tests/` using anonymized sample evidence.
