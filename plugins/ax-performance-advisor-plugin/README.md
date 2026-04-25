# AX Performance Advisor Plugin

AX Performance Advisor is a Codex plugin concept for Dynamics AX 2012 R3 environments running on SQL Server 2016. It is designed to collect evidence, correlate SQL and AX behavior, and generate explainable, auditable recommendations.

## Core USP

The plugin is not another generic SQL monitoring surface. Its value is the AX-aware interpretation layer:

> Correlate SQL Server, AOS, batch jobs, AX tables, business calendars, and change history into explainable, audit-ready performance recommendations for Dynamics AX 2012.

## Detailed USPs

### 1. AX + SQL Correlation

Generic tools usually stop at expensive SQL statements. AX Performance Advisor should connect those statements to AX context:

- Batch job, task, class, batch group, company, and AOS.
- AX table and module context such as inventory, finance, sales, purchasing, retail, AIF, or workflow.
- Time-window correlation between SQL waits, blocking chains, AOS pressure, integrations, and batch schedules.
- Clear wording such as: "Batch job X between 02:00 and 02:45 correlates with PAGEIOLATCH waits and high logical reads on InventTrans."

### 2. AX Knowledge Base And Rule Library

The advisor should include AX-specific rules instead of relying only on generic SQL heuristics:

- High-risk tables: `InventTrans`, `InventSum`, `CustTrans`, `VendTrans`, `SalesLine`, `PurchLine`, `LedgerJournalTrans`, `GeneralJournalAccountEntry`, `Batch`, `BatchJob`, `WorkflowTrackingStatusTable`, `RetailTransactionTable`.
- AX key patterns: `RecId`, `DataAreaId`, `Partition`, date/status fields, voucher/account dimensions, item/site/warehouse dimensions.
- AX workload patterns: MRP, master planning, inventory close, financial posting, retail statement posting, AIF imports, EDI windows, workflow processing, SysOperation framework jobs.
- Known advisory posture: prefer evidence-backed schedule, statistics, and targeted query/index review before broad schema changes.

### 3. Explainable Recommendations

Every recommendation must explain:

- Observed metric and threshold.
- Query, plan, wait, object, batch job, AOS, or export evidence.
- Affected AX table, module, process, or business window.
- Likely cause and confidence.
- Expected effect.
- Implementation risk.
- Validation metric.
- Rollback or no-change fallback.

### 4. Audit-Ready Evidence Packs

For regulated environments, every finding should be exportable as an evidence pack:

- Source files and collection timestamps.
- Hash or identifier for imported evidence bundles.
- Analysis version and rule version.
- Finding severity, confidence, owner, and status.
- Recommendation, approval state, implementation notes, and post-change result.
- Attachments for ITIL, CAB, GxP validation, or internal audit review.

### 5. Before/After Proof

The advisor should not stop after recommending actions. It should support measurable improvement proof:

- Baseline period vs. post-change period.
- Runtime, CPU, logical reads, waits, blocking, deadlocks, TempDB, and file latency deltas.
- Batch duration trend before and after rescheduling or tuning.
- Business-window checks such as month-end close or inventory close.
- Report language that distinguishes improvement, no measurable change, and regression.

### 6. Change Readiness Score

Each proposed action should include a change-readiness score:

- Technical risk.
- AX compatibility risk.
- Regression-test effort.
- Locking or downtime risk.
- Rollback complexity.
- Confidence in expected benefit.
- Business impact if deferred.

This helps separate low-risk operational adjustments from changes needing formal CAB/GxP review.

### 7. AX Anti-Pattern Detection

The advisor should flag common patterns:

- Large table scans on company-scoped tables without `DataAreaId` or `Partition` selectivity.
- High logical reads caused by missing composite index coverage.
- Parameter-sensitive plans with strong runtime variance.
- Batch jobs colliding with maintenance, integrations, reporting, or user peaks.
- X++ row-by-row processing symptoms visible as many repeated short SQL calls.
- Reports or exports reading broad transaction ranges during business hours.
- TempDB pressure from sorting, hashing, version store growth, or large intermediate result sets.
- Recurrent blocking chains around posting, inventory, settlement, or integration jobs.

### 8. Business Calendar Correlation

The plugin should understand that AX performance is not evenly distributed:

- Month-end and year-end close.
- Inventory close and recalculation.
- Master planning and MRP.
- Payroll or finance posting windows.
- Retail statement posting and channel sync.
- EDI/AIF import windows.
- Backup, index, statistics, ETL, and reporting schedules.

This allows findings to describe business risk, not only technical load.

### 9. No-Touch Advisory Mode

Production AX 2012 systems are often fragile and regulated. The default operating model is:

- Read-only collection.
- No automatic schema, SQL, AX, or configuration changes.
- Human approval required before any remediation.
- Generated scripts marked as proposals, not execution commands.
- Evidence and rollback notes included before implementation.

### 10. Legacy Optimization Or Migration Signal

The advisor should separate problems that can be pragmatically optimized from structural legacy limits:

- Tune now: stale statistics, batch collisions, targeted index review, maintenance gaps, blocking root causes.
- Redesign: problematic custom X++, oversized integrations, reporting directly on OLTP, missing archiving strategy.
- Migration signal: recurring architectural pressure that indicates D365 or data-platform modernization should be evaluated.

### 11. Executive Dashboard Potential

The technical analysis should feed an executive dashboard:

- Performance score.
- Top 10 constraints.
- Batch SLA trend.
- SQL wait trend.
- Risk heat map.
- Change backlog.
- Estimated business impact and deferred-risk cost.

### 12. Custom-Code Hotspot Detection

AX 2012 environments often suffer more from customizations than from standard AX behavior. The advisor should identify recurring custom-code hotspots:

- X++ classes, reports, forms, services, custom batch jobs, and custom tables.
- Repeated SQL patterns linked to the same customization.
- Trace Parser evidence that connects call stacks to SQL cost.
- Regression after custom deployments or hotfixes.
- Ownership mapping to the responsible development or process team.

The goal is to say: "This custom report or batch class is the performance driver", not only "this SQL query is expensive."

### 13. Data Growth Advisor

Some problems are data-lifecycle issues, not query-tuning issues. The advisor should detect:

- Rapid table growth and skewed growth by company, item, customer, date, or module.
- Tables with historical data that drives scan cost, index size, maintenance time, backup size, and TempDB pressure.
- Runtime trends that rise with row count.
- Archive or cleanup candidates.
- Missing retention decisions for integrations, retail transactions, workflow history, staging tables, and logs.

Output should distinguish "tune the query" from "reduce or partition the data pressure through an approved lifecycle strategy."

### 14. AX Maintenance Window Optimizer

Nightly windows often combine AX batch, SQL maintenance, backups, ETL, reporting, and integrations. The advisor should optimize the window as a whole:

- Detect overlapping high-load jobs.
- Identify backup/index/statistics maintenance collisions.
- Compare job duration and resource pressure by time slot.
- Recommend safer sequencing, split windows, or AOS/batch-group reassignment.
- Flag windows that are too small for current data volume.

### 15. Module-Specific Health Scores

The plugin should produce module-level scores so technical risk is tied to business ownership:

- Inventory.
- Finance.
- Sales.
- Purchasing.
- Retail.
- Batch.
- Integration.
- Reporting.
- Infrastructure/SQL.

Each score should be explainable through findings, trend, severity, and business impact.

### 16. Performance Debt Register

Findings should persist into a performance debt register:

- Open finding age.
- Recurrence count.
- Deferred risk.
- Affected process.
- Current owner.
- Next decision.
- Target date.
- Validation state.

This turns performance into a managed backlog rather than repeated one-off analysis.

### 17. SLA Breach Prediction

The advisor should use trends to warn before a process misses its window:

- Batch duration growth.
- Close-window compression.
- Data growth vs. runtime growth.
- Wait and blocking recurrence.
- Capacity trend for CPU, memory, I/O, and TempDB.

Example output: "Inventory close duration has grown 6 percent per week; current trend predicts SLA breach in about 5 weeks unless workload or data volume changes."

### 18. Deployment Regression Detector

The advisor should compare performance before and after:

- X++ deployment.
- AX hotfix.
- SQL index or statistics change.
- Configuration change.
- Infrastructure change.
- Batch schedule change.

It should identify improved, unchanged, and regressed metrics with evidence and confidence.

### 19. Table Ownership Mapping

Technical tables should map to business and technical owners:

- `InventTrans` -> Supply Chain / Inventory.
- `GeneralJournalAccountEntry` -> Finance.
- `RetailTransactionTable` -> Retail.
- Custom tables -> owning customization or integration.

This allows findings to be routed to accountable teams and converted into actionable change requests.

### 20. Action Playbooks

Common finding types should generate structured playbooks:

- Stale statistics.
- Blocking chain.
- Batch collision.
- Parameter-sensitive plan.
- Missing composite index candidate.
- TempDB pressure.
- Data growth.
- Custom-code hotspot.
- Deployment regression.
- Environment drift.

Playbooks should include diagnostic confirmation, low-risk mitigations, change proposal, validation, and rollback.

### 21. Risk-Based Index Advisor

Index advice must consider AX realities:

- Read benefit.
- Write overhead.
- Table volume.
- AX model/deployment impact.
- Existing index overlap.
- Maintenance cost.
- Locking risk during creation or rebuild.
- Rollback path.

The output should explicitly separate "candidate worth reviewing" from "recommended for implementation."

### 22. User Experience And Role Correlation

Performance findings should connect to affected users and roles where possible:

- User sessions and client activity.
- Role or department impact.
- Business process affected.
- AOS node and company.
- Peak-hour vs. off-hour impact.

This helps prioritize issues that directly affect operational users over background noise.

### 23. Archive Candidate Detection

The advisor should identify tables and processes where archiving, cleanup, or retention changes may produce better results than tuning:

- Transaction history.
- Workflow and batch history.
- Integration staging.
- Retail transactions.
- Logs and temporary/staging tables.
- Old closed business documents.

Recommendations must include business approval and validation needs because archiving can affect reporting, audit, and legal retention.

### 24. Environment Drift Detection

The advisor should compare production, test, pre-production, and disaster-recovery environments:

- SQL Server settings.
- Database options.
- Index and statistics differences.
- AX batch setup.
- AOS configuration.
- Data volume and data distribution.
- Maintenance jobs.
- Hotfix/build level where available.

This explains why performance issues are not reproducible outside production.

### 25. Capacity Planning For Legacy AX

The advisor should forecast how long the current AX 2012 platform remains operationally safe:

- CPU, memory, I/O, storage, TempDB, and backup trend.
- Batch duration and SLA trend.
- Data growth trend.
- User/session growth.
- Integration volume growth.
- Maintenance-window saturation.

Output should support decisions about hardware, SQL tuning, archiving, workload redesign, or migration planning.

### 26. Compliance-Safe Recommendation Modes

The advisor should support recommendation modes:

- Observe only: collect and summarize evidence.
- Advisory: produce findings and recommendations.
- Change proposal: generate implementation-ready proposal with risk and validation.
- CAB package: produce formal change narrative and evidence pack.
- Post-change validation: measure result and document outcome.

This lets the same plugin serve operational troubleshooting and regulated change-control workflows.

### 27. Noise-Controlled Findings

The advisor should convert noisy monitoring data into a manageable action list by suppressing benign waits, deduplicating repeated symptoms, grouping by root cause, and limiting tickets to approved severities.

### 28. Delta-Based SQL Diagnostics

Wait stats and other cumulative DMVs should be interpreted as interval deltas whenever possible, so reports reflect the current workload rather than historical server uptime.

### 29. Environment Profile As Code

Each environment should have a versioned profile for SQL server, AX database, model database, thresholds, owner mapping, SLA targets, and suppression rules.

### 30. Schema-Adaptive AX Collection

Collectors should adapt to AX 2012 schema differences caused by localization, patch level, customization, or module availability.

### 31. Root-Cause Board

Individual findings should roll up into root-cause groups such as storage pressure, parameter-sensitive plans, stale statistics, data growth, batch collision, and environment drift.

### 32. Evidence Quality Score

Each finding should identify whether evidence is direct, correlated, inferred, or incomplete so reviewers can judge confidence quickly.

### 33. Advisor Self-Diagnostics

Collector failures should become explicit evidence, not hidden errors. The report should show which data sources failed and why.

### 34. Safe Production Sampling

Production collection should be read-only, timeout-aware, top-N bounded, and configurable, with deeper probes enabled explicitly.

### 35. Board-Ready Change Bundles

Findings should feed tickets, CAB packages, evidence packs, validation criteria, rollback notes, and owner routing from one consistent dataset.

## MVP Scope

- SQL Server collector: top queries, wait stats, blocking, index fragmentation, missing indexes, plan cache signals, stale statistics, TempDB and file latency.
- AX collector: batch jobs, AOS events and counters, user sessions, Trace Parser exports, DynamicsPerf data, service and retail load patterns.
- Analysis engine: pattern detection, finding prioritization, risk scoring, and change recommendations.
- Reports: technical Markdown/HTML report, management summary, and optional Power BI export model.

## Finding Model

Each finding should be stored with this logical shape:

- `id`: stable finding identifier.
- `title`: short human-readable finding title.
- `severity`: critical, high, medium, low, informational.
- `confidence`: high, medium, low.
- `businessImpact`: affected process, users, SLA, or close window.
- `evidence`: source, metric, value, threshold, timestamp, and object identifiers.
- `axContext`: table, class, batch job, AOS, company, module, service, or report.
- `sqlContext`: query hash, plan hash, wait type, index, statistic, file, session, or blocking chain.
- `recommendation`: concrete action and owner.
- `changeReadiness`: risk, test effort, downtime, rollback, and approval path.
- `validation`: before/after metric and observation window.
- `status`: proposed, approved, implemented, rejected, deferred, validated.
- `ownership`: business owner, technical owner, support queue, or vendor.
- `performanceDebt`: recurrence, age, deferment reason, and next decision.
- `prediction`: SLA risk, breach horizon, trend confidence, and capacity signal.
- `environmentDrift`: whether the finding depends on production-only differences.
- `playbook`: recommended diagnostic and remediation path.

## Prioritization Logic

Findings should be ranked by:

- Business impact first.
- Reproducibility and evidence quality second.
- Operational risk and reversibility third.
- Cost of delay and recurrence fourth.
- SLA breach risk and performance-debt age fifth.
- Ease of validation sixth.

## Design Principles

- Read-only by default.
- No automatic SQL or AX changes.
- Every recommendation must include evidence, affected objects, expected effect, risk, validation steps, and rollback guidance.
- AX-aware advice must consider RecId, DataAreaId, Partition, AX table semantics, batch scheduling, and regulatory change-control requirements.
- The plugin must distinguish facts, inferred causes, and recommended actions.
- Recommendations should prefer reversible operational changes before invasive schema or X++ changes.

## Initial Skills

- `ax-performance-analysis`: end-to-end SQL and AX correlation.
- `sql-server-query-tuning`: SQL Server 2016 evidence interpretation for AX workloads.
- `batch-job-optimization`: AX batch and SysOperation performance analysis.
- `management-report-generator`: CIO-ready summaries and ITIL/GxP change narratives.

## AI/KI Feature Pack

The plugin includes a real local AI/KI advisory layer in `scripts/ai_insights.py`. It is deterministic and evidence-grounded: no external LLM call is required, and every output is derived from AXPA findings.

Run it with:

```powershell
python .\scripts\ai_insights.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\IT-TEST-ERP4CU-ai-insights.json `
  --markdown-output .\out\IT-TEST-ERP4CU-ai-insights.md `
  --question "Warum war AX langsam?"
```

Implemented AI/KI features:

- Natural-language root-cause chat.
- Finding explainer for technical, key-user, and management audiences.
- Change risk predictor.
- Batch scheduler optimizer.
- Query-to-AX-code mapping.
- Regression detector.
- Remediation planner.
- Evidence gap detector.
- Incident summary generator.
- GxP validation assistant.
- Runbook copilot.
- Noise reduction and grouping.
- Business impact estimator.
- Knowledge-base learning candidates.
- Anomaly forecasting candidates.
- D365 migration signal map.
- Ticket auto-drafting.
- Executive narrative.
- SQL plan interpreter.
- Safe action classifier.

Details are documented in `docs/ai-ki-features.md`.

The interactive HTML dashboard embeds this AI/KI pack in dedicated tabs for advisory chat, safe actions, GxP validation, evidence gaps, ticket drafts, and collector status.

Release and local test instructions are documented in `docs/release-runbook.md`. Additional future differentiation ideas are tracked in `docs/future-ai-usps.md`.

Admin Execution Mode is documented in `docs/admin-execution-mode.md`. It generates guarded preview scripts, confirmation tokens, and audit records for approved admins without executing production changes from the dashboard.

Enterprise Observability is documented in `docs/enterprise-observability.md`. It adds time-series storage, alerts, estate inventory, query/plan repository, and notification payload exports.

Optional agent, RBAC portal, local RAG/Q&A, X++ attribution, and release packaging are documented in `docs/optional-agent-rbac-rag-release.md`. The agent remains optional and is not required to install or run the plugin.

Advanced operational USPs are documented in `docs/advanced-usps.md`, including SLO burn rate, maintenance-window sequencing, cost of delay, release gates, retention candidates, known-issue matching, and executive briefings.

Governance extensions are documented in `docs/governance-extensions.md`, including runbook automation, RACI, business impact timeline, suppression governance, data quality checks, and audit exports.

Strategy extensions are documented in `docs/strategy-extensions.md`, including what-if simulation, baseline benchmark, evidence roadmap, remediation Kanban, KPI contracts, and capability matrix.

Additional AI/KI extensions are documented in `docs/ai-ki-extensions.md`, including hypothesis ranking, counterfactuals, causal narrative, LLM context packs, evidence chunks, and confidence calibration.

Market differentiator USPs are documented in `docs/market-differentiators.md`, including vendor-neutral comparison, migration readiness, resilience score, knowledge graph, process owner scorecards, evidence marketplace, and value realization.

The local RBAC web portal and LLM connector are documented in `docs/web-portal-and-llm.md`.

## Planned Extensions

- AX rule-library files for table families, workload windows, and anti-patterns.
- Evidence-pack exporter for audit and change-management workflows.
- Before/after comparator for deployments and tuning actions.
- Power BI dataset export for executive reporting.
- Azure DevOps or Jira ticket generation for approved findings.
- Performance debt register.
- SLA breach predictor.
- Deployment regression detector.
- Environment drift comparator.
- Table ownership and action playbook library.
