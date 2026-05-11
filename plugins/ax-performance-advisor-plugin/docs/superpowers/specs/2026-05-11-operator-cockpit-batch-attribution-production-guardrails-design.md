# AXPA Operator Cockpit, Batch Control Tower, Attribution, and Production Guardrails

Date: 2026-05-11
Status: design for review
Scope: Dynamics AX 2012 R3 CU13 + SQL Server 2016 performance advisor plugin

## Goal

Expand AX Performance Advisor from a feature-rich technical dashboard into an operator-ready diagnostic system. The next version must make BRAS3333-style incidents easier to understand, safer to collect, and more actionable without ever writing to the queried AX or SQL Server databases.

The implementation is split into four waves so the system remains usable and testable:

1. Operator Cockpit and Safety Guard
2. Batch Control Tower
3. X++ / AX Attribution Deep Mode
4. Daily Production Loop

## Non-Negotiable Safety Rules

The plugin may only write local files in the workspace, for example under `evidence/`, `out/`, and `docs/`.

It must not write to the queried AX or SQL Server databases. No collector may execute database-changing statements such as `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, or operational `EXEC` commands that perform changes. Dynamic SQL is only acceptable when it wraps read-only `SELECT` statements and is explicitly marked as such by the safety scanner.

If the connected SQL principal has excessive rights, the dashboard must show a visible warning. The run can continue only in read-only collector mode.

Admin execution remains preview-only unless a separate, explicit, local workflow approval is present. Even then, AXPA produces scripts, checklists, validation instructions, and audit records locally; it does not execute changes against the production database.

## Wave 1: Operator Cockpit and Safety Guard

### User Problem

The current dashboard has many strong features, but a user must know which tab to open and how to interpret many technical sections. Operators need a first screen that answers:

- What is the biggest problem right now?
- Who or what is likely causing it?
- Which business process is affected?
- What can I safely do now?
- What must I not do without approval?

### Design

Add an `Operator Cockpit` as the default first view. It summarizes the run into a small number of decision cards:

- `Current Situation`: health score, high/critical count, live blocking state, batch collision state.
- `Top Suspect`: best current root cause with confidence, evidence count, and affected module.
- `Affected Context`: user, AOS/host, session, batch group, table, query hash where available.
- `Safe Next Action`: one to three immediate actions that do not change AX or SQL data.
- `Do Not Do`: explicit warnings, such as "do not kill session without owner confirmation" or "do not create missing-index DMV recommendation directly in PROD".
- `Evidence Missing`: exact collector or file needed to improve confidence.

Add `Safety Guard` output to every run:

- SQL rights check: read permissions plus risky rights such as `CREATE TABLE` or `ALTER ANY SCHEMA`.
- Collector SQL verb scan.
- Collector mode: `read-only`, `read-only-with-dynamic-select`, `blocked`, or `unknown`.
- Local output path confirmation.
- Production safety verdict: green, amber, red.

### Data Flow

Existing findings, platform extensions, operational status, evidence health, and live flight recorder data feed a new `operator_cockpit` module. Safety Guard reads collector scripts and permission CSVs, then emits `out/<run>/operator-safety-guard.json`.

The dashboard renders both sections near the top, before advanced tabs.

### Acceptance Criteria

- Dashboard has a default `Operator Cockpit` section before or inside the first visible view.
- User can identify the top issue and safe next action in under one minute.
- Safety Guard shows a warning when the SQL login has excessive rights.
- Safety Guard confirms no DB writes are executed by collectors.
- Tests cover the safety scanner for harmless read-only dynamic SQL and blocked write verbs.

## Wave 2: Batch Control Tower

### User Problem

BRAS3333 shows real batch pressure: MRP, LOG, LOG2, Reports and other groups collide. The dashboard currently has proposals, but batch users need a dedicated control tower with dependencies, SLA context, and precise move recommendations.

### Design

Add `Batch Control Tower` with:

- `Collision Map`: heatmap by hour and group.
- `Dependency Graph`: inferred job chains and "do not move before/after" hints.
- `SLA Contract Manager`: batch group, target finish time, business owner, escalation note.
- `Reschedule Simulator`: current hour, target hour, expected peak reduction, risk note, validation, rollback.
- `AOS Affinity Advisor`: recommended AOS placement for heavy groups based on observed load and sessions.
- `Change Candidate Pack`: local TEST-only change plan for each proposal.

The BRAS3333 examples should be presented as concrete candidates:

- Reports 16:00 -> 21:00
- LOG2 04:00 -> 23:00
- LOG2 17:00 -> 21:00
- LOG 03:00 -> 23:00
- MRP 15:00 -> 21:00

Each proposal must include:

- source window and target window
- exact group and sample task captions
- expected overlap reduction
- dependency risk
- TEST validation checklist
- rollback condition

### Data Flow

`batch_tasks.csv`, `batch_jobs.csv`, `ax_live_blocking.csv`, Query Store runtime, and findings feed a new `batch_control_tower` module. The module emits `out/<run>/batch-control-tower.json` and dashboard visual sections.

### Acceptance Criteria

- Batch Control Tower shows at least hourly load, group load, and top move candidates.
- Every move candidate includes risk, validation, rollback, and example tasks.
- No candidate is presented as an automatic production change.
- Tests cover collision ranking, target slot selection, and proposal text generation.

## Wave 3: X++ / AX Attribution Deep Mode

### User Problem

The strongest long-term USP is precise attribution: SQL query to AX form, class, method, batch job, user, and business process. Today this is partly inferred from SQL patterns and session data.

### Design

Add an `Attribution Engine` with confidence scoring:

- `SQL Pattern Attribution`: uses query text, tables, dimensions, query hash, plan hash.
- `Session Attribution`: uses AX live blocking, SQL sessions, host, login, program name, session id.
- `Batch Attribution`: maps batch tasks/jobs/groups to SQL time windows and tables.
- `Form Inference`: maps InventSum/InventDim patterns to likely forms such as InventOnHand.
- `Deep Source Inputs`: optional `trace_parser.csv`, `dynamicsperf.csv`, `ax_model_mapping.csv`, and AX model mapping.
- `Confidence Ladder`: direct proof, strong inference, weak inference, missing evidence.

The output should explicitly separate facts from inference:

- `Observed`: data directly present in evidence.
- `Inferred`: likely AX object or form based on rules.
- `Missing Proof`: exact data needed to verify.
- `Next Collector`: collector or export to run.

### Data Flow

Existing `flight_recorder`, `axpa_core`, model mapping, Trace Parser and DynamicsPerf import paths feed a new `attribution_engine` module. It emits `out/<run>/attribution-engine.json`.

### Acceptance Criteria

- Each top SQL finding has an attribution object.
- Attribution includes confidence score and evidence class.
- Dashboard never presents inferred form/class/method as fact.
- If Trace Parser/DynamicsPerf files are missing, the dashboard explains what proof is missing.
- Tests cover at least wide inventory, finance posting, warehouse, sales, and unknown SQL patterns.

## Wave 4: Daily Production Loop

### User Problem

To be useful operationally, AXPA needs a reliable daily loop: collect, analyze, compare to previous runs, show deltas, and optionally push summaries to external systems. Current push and scheduler checks exist but are not yet fully operational.

### Design

Add `Daily Production Loop`:

- `Scheduler Readiness`: task exists, last success, lockfile clear, last duration, failure reason.
- `Daily Delta`: new findings, resolved findings, worsened findings, improved findings.
- `Trend Summary`: health score, high findings, batch collisions, peak concurrency, Query Store regressions.
- `Push Readiness`: Teams, ADO, Jira, ServiceNow, Power BI configuration status.
- `Dry-run First`: all pushes must support dry-run with duplicate detection and audit record.
- `Runbook Output`: a local daily Markdown report for IT operations.

Production integrations stay optional. Missing Teams/ADO/Jira/ServiceNow/PowerBI credentials must not block local analysis.

### Data Flow

Pipeline manifest, trend SQLite DB, operational status, push readiness, dashboard QA, and readiness pack feed a new `daily_production_loop` module. It emits `out/<run>/daily-production-loop.json` and a Markdown daily summary.

### Acceptance Criteria

- Daily loop can run without external push configuration.
- Missing push credentials are shown as configuration gaps, not analysis failures.
- Trend diff identifies new and recurring issues.
- Scheduler health is visible in the dashboard.
- Tests cover missing scheduler, missing push credentials, successful dashboard QA, and daily delta generation.

## Dashboard Information Architecture

The dashboard should move from many equal tabs to a task-based flow:

1. Operator Cockpit
2. Problems
   - Batch
   - Blocking
   - Frontend/Machine Impact
   - Query/Plan/Stats
3. Recommendations
   - Safe Actions
   - Batch Moves
   - TEST Plans
   - CAB Packs
4. Evidence
   - Evidence Health
   - Attribution Confidence
   - Missing Proof
5. Operations
   - Scheduler
   - Push Readiness
   - Safety Guard
   - Audit
6. Advanced
   - Platform
   - AI/KI
   - Strategy
   - Skills

This does not remove advanced features. It changes the default path so normal users start with decisions, while power users can still inspect details.

## Error Handling

- Missing collector files produce evidence gaps, not crashes.
- Empty CSVs are treated as valid "no rows observed" evidence.
- SQL permission warnings are shown separately from collector failures.
- Dashboard generation must continue even when optional modules cannot produce results.
- Push integration failures must not prevent local reports.

## Testing Plan

Add focused tests for:

- Safety scanner classification.
- Operator cockpit top-suspect selection.
- Batch proposal ranking and target-hour selection.
- Attribution confidence classes.
- Daily delta from two runs.
- Dashboard marker checks for the new sections.

Keep current regression tests passing.

## Out of Scope for This Design

- Automatic production schema changes.
- Automatic index creation.
- Automatic session killing.
- Direct writes to AX or SQL Server databases.
- Mandatory external cloud integrations.
- Replacing Trace Parser or DynamicsPerf; AXPA can consume their exports but does not require them.

## Implementation Order

1. Add Safety Guard and Operator Cockpit JSON modules.
2. Render Operator Cockpit and Safety Guard in the dashboard.
3. Add Batch Control Tower module and dashboard views.
4. Add Attribution Engine with confidence ladder.
5. Add Daily Production Loop and trend delta.
6. Extend docs and tests.

## Review Notes

This design intentionally prioritizes safety and operator usability first. It keeps advanced AI/KI and platform modules, but routes users through clearer operational questions:

- What is happening?
- Why do we think that?
- What proof is missing?
- What is the safe next step?
- What is the TEST-only change candidate?
