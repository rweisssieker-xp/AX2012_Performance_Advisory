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

## Prioritization Logic

Findings should be ranked by:

- Business impact first.
- Reproducibility and evidence quality second.
- Operational risk and reversibility third.
- Cost of delay and recurrence fourth.
- Ease of validation fifth.

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

## Planned Extensions

- AX rule-library files for table families, workload windows, and anti-patterns.
- Evidence-pack exporter for audit and change-management workflows.
- Before/after comparator for deployments and tuning actions.
- Power BI dataset export for executive reporting.
- Azure DevOps or Jira ticket generation for approved findings.
