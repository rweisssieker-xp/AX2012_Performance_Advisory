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

## USP 12: Custom-Code Hotspot Detection

The advisor should identify expensive custom X++ classes, reports, services, forms, custom batch jobs, and custom tables. Trace Parser and DynamicsPerf evidence should be used to connect SQL cost to the responsible customization whenever possible.

## USP 13: Data Growth Advisor

The advisor should identify data-growth patterns that explain rising runtimes, maintenance pressure, backup growth, index bloat, and scan cost. It should recommend archive or retention review when data lifecycle is a better lever than query tuning.

## USP 14: AX Maintenance Window Optimizer

The advisor should analyze AX batch, SQL maintenance, backups, ETL, integrations, and reports as one operating window. It should recommend sequencing and workload distribution rather than treating each job in isolation.

## USP 15: Module-Specific Health Scores

The advisor should produce scores for inventory, finance, sales, purchasing, retail, batch, integration, reporting, and SQL/infrastructure. Each score must be explainable through underlying findings and trends.

## USP 16: Performance Debt Register

The advisor should persist recurring findings into a debt register with age, recurrence, owner, risk, deferred decision, business impact, and validation state.

## USP 17: SLA Breach Prediction

Trend analysis should predict when critical batch jobs, close windows, integrations, or maintenance processes are likely to breach their SLA.

## USP 18: Deployment Regression Detector

The advisor should detect performance changes after deployments, hotfixes, index changes, configuration changes, infrastructure changes, and batch schedule changes.

## USP 19: Table Ownership Mapping

The advisor should map technical AX tables and custom objects to business and technical owners so findings can be routed directly to accountable teams.

## USP 20: Action Playbooks

The advisor should produce playbooks for common findings such as stale statistics, blocking chains, batch collisions, parameter-sensitive plans, TempDB pressure, data growth, custom-code hotspots, deployment regressions, and environment drift.

## USP 21: Risk-Based Index Advisor

Index recommendations should be ranked by read benefit, write overhead, table volume, deployment path, existing index overlap, maintenance cost, locking risk, and rollback complexity.

## USP 22: User Experience And Role Correlation

The advisor should connect technical findings to user sessions, roles, departments, companies, AOS nodes, and business processes where the evidence allows it.

## USP 23: Archive Candidate Detection

The advisor should identify tables and workloads where archive, cleanup, or retention changes are more appropriate than additional tuning.

## USP 24: Environment Drift Detection

The advisor should compare production, pre-production, test, and disaster-recovery environments to explain non-reproducible performance issues.

## USP 25: Capacity Planning For Legacy AX

The advisor should forecast CPU, memory, I/O, storage, TempDB, backup, batch, user-load, integration, and data-growth pressure to support legacy platform planning.

## USP 26: Compliance-Safe Recommendation Modes

The advisor should support observe-only, advisory, change-proposal, CAB-package, and post-change-validation modes.

## USP 27: Noise-Controlled Findings

The advisor should suppress benign waits, deduplicate repeated symptoms, group findings by root cause, and produce an actionable top list instead of flooding operators with raw DMV noise.

## USP 28: Delta-Based SQL Diagnostics

The advisor should prefer interval deltas for waits and runtime evidence over cumulative DMV totals. This separates current workload pressure from historical residue.

## USP 29: Environment Profile As Code

Every customer environment should be described by a versioned profile containing SQL server, AX database, model database, thresholds, SLA targets, owner mapping, and suppression rules.

## USP 30: Schema-Adaptive AX Collection

AX 2012 systems vary by layer, customization, localization, and patch level. Collectors should detect columns and tables dynamically instead of assuming one fixed schema.

## USP 31: Root-Cause Board

The advisor should aggregate individual findings into root-cause groups such as storage pressure, stale statistics, parameter-sensitive plans, batch collision, data growth, and environment drift.

## USP 32: Evidence Quality Score

Findings should show whether the evidence is direct, correlated, inferred, or incomplete. This helps reviewers distinguish proven causes from candidates.

## USP 33: Advisor Self-Diagnostics

Collector failures should be first-class outputs. If Query Store, AIF, sessions, deadlocks, or fragmentation collection fails, the report should state why and what access/schema issue blocked it.

## USP 34: Safe Production Sampling

Collectors should support bounded, read-only, timeout-aware sampling with top-N limits and optional deeper probes, so production systems are not stressed by diagnostics.

## USP 35: Board-Ready Change Bundles

The advisor should generate CAB packages, ticket backlogs, evidence packs, validation criteria, rollback notes, and owner routing from the same finding set.

## USP 36: Performance Flight Recorder

Scheduled lightweight evidence snapshots create a timeline before, during, and after incidents.

## USP 37: Incident Replay

Evidence packs can be replayed as a timeline with workload fingerprint, root-cause chain, and top findings.

## USP 38: Customization Risk Map

Custom X++ objects, reports, services, and custom tables are ranked by performance risk and ownership.

## USP 39: Batch Schedule Simulator

Batch jobs can be analyzed as a conflict matrix with recommended sequencing and AOS/batch-group separation.

## USP 40: Workload Fingerprinting

The advisor classifies windows such as month-end close, MRP, retail posting, integration, and reporting peaks.

## USP 41: AX Table Heatmap

Tables are scored by reads, data growth, stale statistics, missing-index signals, and blocking signals.

## USP 42: Change Risk Simulator

Planned changes such as index, batch move, statistics update, and archiving receive benefit/risk/validation/rollback profiles.

## USP 43: Self-Calibrating Thresholds

Thresholds can be calibrated from local evidence percentiles rather than hard-coded generic limits.

## USP 44: Known-Issue Matching

Findings are matched to an AX-specific known-issue library with fix paths and validation criteria.

## USP 45: Data Lifecycle ROI

Archive and cleanup candidates include estimated reclaimable data volume and business-review requirements.

## USP 46: Test Repro Builder

Production-only issues generate a test-vs-prod reproduction checklist.

## USP 47: Performance Budgeting

Queries and batches are checked against configured performance budgets.

## USP 48: Continuous Improvement Scorecard

Performance governance can be tracked through open findings, high-risk items, regressions, and validated closures.

## USP 49: AX-Specific Index Governance

Index candidates are managed through candidate-review, approval, implementation, validation, and rollback states.

## USP 50: Risk-Aware Auto-Triage

Findings are automatically routed to immediate treatment, next maintenance window, observation, accepted risk, or architecture topic.
