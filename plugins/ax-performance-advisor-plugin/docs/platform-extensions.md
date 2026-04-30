# Platform Extensions

The platform extension layer closes the remaining product gaps against broad database observability tools while keeping AXPA read-only by default.

Generated artifact:

```powershell
python .\scripts\platform_extensions.py `
  --evidence .\evidence\prod-snapshot `
  --output-dir .\out\prod-platform `
  --trend-db .\out\prod-trends.sqlite `
  --manifest .\out\prod-pipeline-manifest.json
```

The normal pipeline runs this step automatically and writes:

- `out/<environment>-platform/platform-extensions.json`
- an embedded `Platform` tab in `out/<environment>-dashboard.html`

## Implemented Features

1. Historisches Trend-Dashboard
   - Reads the SQLite trend store created by `update_trend_store.py`.
   - Shows Health Score, finding counts, high findings, batch collisions, peak batch concurrency, and Query Store risk groups over the last runs.

2. Recommendation Lifecycle
   - Converts findings into operational workflow states.
   - Tracks `proposed -> accepted -> needs_evidence -> in_test -> ready_for_test -> approved -> implemented -> verified -> deferred/rejected`.
   - Uses severity, confidence, approval path, owners, validation metric, and rollback fields from real findings.
   - Supports a JSON state file so operator decisions can survive future runs.

3. Incident Replay Timeline
   - Builds a chronological timeline from batch tasks, live blocking, Query Store runtime rows, and generated findings.
   - Helps answer what happened first, what overlapped, and which finding belongs to which time window.
   - Adds collector events, SQL wait spikes, and AI Incident Commander proof steps.

4. Query Plan Diff / Regression Watch
   - Reads `plan_xml_inventory.csv` and `query_store_runtime.csv`.
   - Flags query or plan families with multiple plan hashes or Query Store plan IDs.
   - Extracts new-plan, scan, lookup, parallelism, and Query Store hotspot/regression signals when present in evidence.

5. Deadlock Graph Visualizer
   - Reads `deadlocks.csv`.
   - Parses deadlock XML into victim, process nodes, resource nodes, and owner/waiter edges.
   - If no deadlocks exist, the module remains real but reports zero available deadlocks.

6. AOS Topology Map
   - Correlates user sessions, batch tasks, and live blocking by AOS/host.
   - Produces node-level session count, batch count, blocked rows, top batch groups, wait pressure, graph edges, and risk.

7. Scheduler Hardening
   - Checks the pipeline manifest status and reports hardening gaps.
   - Covers real lock-file protection, retention guidance, retry policy, exit-code monitoring, last successful run, and health check readiness.

8. Productive Push Readiness
   - Generates integration-ready payload counts, field mapping, dedupe keys, and audit records for Power BI, Teams, Azure DevOps, Jira, and ServiceNow.
   - Switches to `ready-to-push` when required environment variables are configured.
   - Does not transmit data without credentials and explicit configuration.

9. X++ Attribution
   - Uses Trace Parser or DynamicsPerf CSV evidence when available.
   - Maps SQL query/table signals to Trace Parser, DynamicsPerf, AX model mapping, batch/user context, and business process.
   - Reports low-confidence attribution when those sources are absent, instead of inventing class or method names.

10. Environment Drift Guard
    - Verifies core evidence source presence and size.
    - Supports TEST-vs-PROD comparison workflows for indexes, Query Store, batch configuration, AOS assignment, SQL settings, statistics age, and data volume.

11. AI Decision Cockpit
    - Converts current findings into CIO/CAB decision prompts.
    - Summarizes this-week decision groups, risk if deferred, and explicit non-goals.
    - Includes AI Incident Commander, AI Batch Twin, CAB brief, Root Cause Confidence Ladder, Query-to-X++ mapping inputs, Safe Remediation Planner, Regression Watch, Process Owner Briefings, Evidence Quality Coach, and Modernization Signal.

12. Live Batch Collision Watch
    - Converts `batch_tasks.csv` overlap evidence into live-watch style alerts.
    - Reports peak concurrency, peak window, severity, affected batch groups, overlap seconds, and recommended refresh cadence.

13. Batch Reschedule Calendar
    - Builds an hour-by-hour batch calendar from real AX batch task start/end times.
    - Suggests concrete group moves from overloaded hours and estimates overlap reduction.
    - Explains why a group should move, why the target slot is lower risk, and which example tasks are affected.

14. AX Batch Dependency Graph
    - Builds job chains from `batch_jobs.csv` and `batch_tasks.csv`.
    - Detects group transitions such as `INVENT -> MRP` inside the same job chain.
    - Flags reschedule risks when a proposed move could split dependent batch groups.
    - Adds validation guidance before accepting Batch Reschedule Calendar proposals.

15. SQL Blocking Chain Recorder
    - Reads `ax_live_blocking.csv` and `blocking.csv`.
    - Stores root blocker, victim sessions, host/user context, wait type, wait time, and statement text for replay.

16. AX Business Process SLA
    - Aggregates findings by AX business process or module.
    - Produces red/amber/green SLA status, high-risk counts, risk points, and dominant playbooks.

17. Evidence Gap Assistant
    - Shows exactly which collector/file is missing for deep X++ attribution, deadlock visualization, regression guard, blocking recorder, and batch simulation.
    - Includes when to collect each source and why it matters.

18. Deployment Regression Guard
    - Uses Query Store runtime plus plan diff/trend data to identify plan changes, runtime hotspots, and regression candidates.
    - Works as a before/after deployment evidence gate when trend runs exist.

19. Admin Remediation Workbench
    - Creates admin-review action records for top findings.
    - Separates SQL review scripts from AX review tasks and keeps execution outside the read-only advisor path.

20. Alerting Rules
    - Generates concrete Teams/E-Mail/Webhook rule definitions for blocking, batch collisions, Query Store regressions, TempDB pressure, and health-score drops.
    - Reports which rules are active based on available evidence sources.

21. AI Safe Feature Bundle
    - Combines AI Incident Commander, AI Root Cause Confidence Ladder, AI Safe Remediation Planner, AI Batch Twin, AI Change Board Brief, and AI Regression Watch.
    - Uses existing findings, incident timeline, batch evidence, and Query Store/plan evidence. It does not invent missing evidence.

22. Gap Closure - letzte 10 reale Features
    - Adds an explicit readiness and execution view for the remaining product gaps.
    - Covers deadlock capture, Trace Parser/DynamicsPerf/X++ attribution, Retail data status, productive push execution, admin execution gates, scheduler installation, trend quality, dependency-aware batch rescheduling, optional LLM/RAG copilot, and GitHub/release readiness.
    - Each item includes current status, concrete command or next action, missing configuration/evidence, and the dashboard effect.

23. Strategic USP Pack
    - Combines ten high-value differentiators into one executive/operations view.
    - Includes AX Batch Dependency Graph, Batch SLA Contract Manager, Deadlock-to-AX-Process Attribution, AOS Affinity Advisor, Data Growth / Archiving ROI, Change Simulation Queue, Evidence SLA, Known-Issue Matcher for AX 2012 CU13 patterns, Operational Maturity Score, and D365 Migration Signal Dashboard.
    - Uses existing evidence and findings; missing sources remain marked as low-confidence instead of being fabricated.

## Real vs External

All modules above derive their output from local evidence, generated findings, the trend SQLite database, or pipeline manifests.

External publishing is intentionally not automatic. Power BI, Teams, Azure DevOps, Jira, and ServiceNow are `payload-ready` until credentials, destination IDs, and approval policies are configured.

## Lifecycle CLI

Recommendation state changes are persisted with:

```powershell
python .\scripts\manage_recommendation_lifecycle.py `
  --state-file .\out\prod-recommendation-lifecycle-state.json `
  --finding-id AXPA-12345678 `
  --state accepted `
  --actor reinerw `
  --note "Accepted for TEST validation"
```

Allowed states are:

`proposed`, `accepted`, `needs_evidence`, `in_test`, `ready_for_test`,
`approved`, `implemented`, `verified`, `deferred`, `rejected`.

## Productive Push Hub

Use the push hub for external systems. It performs duplicate detection and writes
an audit record before/after each push:

```powershell
python .\scripts\push_integrations.py `
  --evidence .\evidence\prod-snapshot `
  --targets teams,ado,jira,servicenow,powerbi `
  --audit-db .\out\prod-push-audit.sqlite `
  --limit 20
```

Use `--dry-run` to validate payloads, dedupe keys, and audit behavior without
sending data.

Required environment variables:

- Teams: `AXPA_TEAMS_WEBHOOK_URL`
- Azure DevOps: `AXPA_ADO_ORG`, `AXPA_ADO_PROJECT`, `AXPA_ADO_TOKEN`
- Jira: `AXPA_JIRA_BASE_URL`, `AXPA_JIRA_PROJECT`, `AXPA_JIRA_EMAIL`, `AXPA_JIRA_TOKEN`
- ServiceNow: `AXPA_SN_INSTANCE_URL`, `AXPA_SN_TOKEN`
- Power BI: `AXPA_POWERBI_ENDPOINT`

Security/RBAC is intentionally not part of this module.

## Dashboard

The dashboard `Platform` tab renders all platform extension sections:

- trend lines as recent value series,
- lifecycle state counts and next gates,
- incident replay events,
- plan variance and operator flags,
- deadlock records,
- AOS node risks,
- scheduler hardening checks,
- push readiness,
- X++ attribution confidence,
- drift guard source checks,
- AI decision prompts.
- live batch collision alerts,
- batch reschedule calendar proposals,
- AX batch dependency graph and move-risk validation,
- blocking-chain recorder output,
- AX business process SLA status,
- evidence gaps,
- deployment regression guard,
- admin remediation workbench actions,
- alerting rules,
- bundled AI/KI safe-operation features.
- strategic USP pack for SLA, affinity, archiving ROI, maturity and modernization decisions.
- gap-closure status for the last 10 real feature gaps.

This gives AXPA a differentiated layer beyond SQL monitoring: evidence-backed AX operational guidance, batch collision context, approval gates, and management-ready decisions.

## Gap Closure Details

The `gapClosure` payload is designed to avoid "mock complete" claims. It marks each of the remaining ten areas as active, ready, or needing a specific evidence/configuration step.

| Area | What it checks | Concrete next action |
| --- | --- | --- |
| Deadlock capture | `deadlocks.csv` row count and graph readiness | Create SQL Extended Events session for `xml_deadlock_report`, then collect `.xel`/deadlock rows. |
| X++ trace attribution | Trace Parser, DynamicsPerf and AX model mapping rows | Export call tree during slow batch window and map SQL table/query to AX class/method. |
| Retail load status | `retail_load.csv` size and source status | Mark Retail not used or fix Retail collector predicates if Retail is in scope. |
| Productive push execution | Teams/ADO/Jira/ServiceNow/PowerBI dry-run and env vars | Run `push_integrations.py --dry-run`, then configure credentials and destination mapping. |
| Admin execution gate | Lifecycle state and TEST-only execution rules | Move findings through lifecycle to `approved`, then generate review scripts and before/after evidence. |
| Scheduler install | Manifest, lock, retention and healthcheck readiness | Install Windows Task Scheduler command and monitor pipeline manifest status. |
| Trend quality | Trend run count and quality grade | Schedule recurring snapshots until trends have enough runs for regression confidence. |
| Batch dependency-aware reschedule | Concrete move proposals plus dependency risk | Add predecessor/successor metadata from AX batch config before changing schedules. |
| LLM/RAG copilot | Local context readiness and guardrails | Use masked evidence packs and require source-cited answers; no execution from chat output. |
| GitHub/release readiness | Release checklist and required repository files | Run final tests, audit generated/source files, update quickstart and release notes. |

The same information is also exported as an operator action pack:

- `out/<environment>-platform/gap-closure-actions.json`
- `out/<environment>-platform/gap-closure-actions.md`

Useful commands:

```powershell
sqlcmd -S <server> -E -i .\scripts\setup_deadlock_capture.sql

powershell .\scripts\install_windows_task.ps1 `
  -Environment prod `
  -Server sql-prod `
  -Database MicrosoftDynamicsAX `
  -Evidence .\evidence\prod-current `
  -Out .\out `
  -At 02:00

python .\scripts\push_integrations.py `
  --evidence .\evidence\prod-current `
  --targets teams,ado,jira,servicenow,powerbi `
  --audit-db .\out\prod-push-audit.sqlite `
  --dry-run
```
