# USP Catalog

This catalog defines the differentiators that should guide future implementation work.

## Primary Promise

AX Performance Advisor turns disconnected AX 2012 and SQL Server evidence into explainable, audit-ready performance decisions.

## USP 1: AX + SQL Correlation

The advisor should correlate:

- SQL waits, top queries, blocking, deadlocks, TempDB, I/O latency, missing indexes, stale statistics, and plan-cache behavior.
- AOS counters, event logs, user sessions, batch history, services, retail workloads, and DynamicsPerf or Trace Parser exports.
- AX tables, modules, companies, batch classes, AOS nodes, and business windows.

Expected result: "Which AX process caused which SQL symptom, when, how often, and with what business risk?"

## USP 2: AX Rule Library

The rule library should encode AX-specific knowledge:

- Table families and high-risk transaction tables.
- Common key and filter patterns involving `Partition`, `DataAreaId`, `RecId`, status, date, dimensions, and voucher fields.
- Batch and SysOperation behavior.
- Integration, retail, workflow, reporting, and posting patterns.
- Known false positives from generic SQL tooling.

## USP 3: Explainable Recommendations

No recommendation should be a black box. Each must show:

- Evidence.
- AX context.
- Likely cause.
- Confidence.
- Expected effect.
- Risk.
- Validation.
- Rollback.

## USP 4: Audit Evidence Packs

The advisor should generate a portable evidence pack for every formal analysis:

- Raw evidence and hashes.
- Rule and analysis versions.
- Findings and recommendations.
- Approval and implementation status.
- Before/after validation.
- Exportable artifacts for ITIL, CAB, QA, and audit.

## USP 5: Before/After Proof

The advisor should measure whether an action worked:

- Baseline vs. post-change runtime.
- CPU, reads, waits, blocking, deadlocks, TempDB, and I/O deltas.
- Batch SLA improvement.
- Business-period impact.
- Regression detection.

## USP 6: Change Readiness Score

Every action should be scored across:

- Benefit.
- Confidence.
- Technical risk.
- AX compatibility risk.
- Regression-test effort.
- Downtime or locking risk.
- Rollback complexity.
- Approval path.

## USP 7: AX Anti-Pattern Detection

Detection targets:

- Broad scans on high-volume AX tables.
- Missing company or partition selectivity.
- Parameter-sensitive plans.
- Batch collisions.
- Repeated short SQL calls suggesting row-by-row X++ behavior.
- Reporting against OLTP tables during business hours.
- TempDB pressure from sorts, hashes, or large intermediate sets.
- Recurring blocking roots.

## USP 8: Business Calendar Correlation

Performance should be interpreted against:

- Month-end and year-end close.
- Inventory close and recalculation.
- Master planning and MRP.
- Retail statement posting.
- EDI and AIF windows.
- Backups, ETL, reporting, and maintenance.

## USP 9: No-Touch Advisory Mode

The plugin defaults to read-only collection and advisory output. It must not execute remediation automatically. Generated remediation scripts are proposals until explicitly reviewed and approved.

## USP 10: Optimize Or Modernize Signal

The advisor should classify findings as:

- `tune-now`: low-risk optimization likely to help.
- `redesign-needed`: custom code, process, or architecture issue.
- `migration-signal`: repeated structural pressure suggesting modernization or D365 evaluation.

## USP 11: Executive Dashboard

Dashboard-ready output should include:

- Performance score.
- Top constraints.
- Batch SLA trend.
- Wait trend.
- Risk heat map.
- Change backlog.
- Business impact.
- Deferred-risk view.
