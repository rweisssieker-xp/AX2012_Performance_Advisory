---
name: ax-performance-analysis
description: Analyze Dynamics AX 2012 R3 performance by correlating SQL Server, AOS, batch, Trace Parser, and DynamicsPerf evidence into prioritized explainable findings.
---

# AX Performance Analysis

Use this skill when diagnosing AX 2012 R3 performance issues, creating a daily health check, or turning monitoring exports into concrete recommendations.

## Positioning

The goal is AX-specific interpretation, not generic metric narration. Always connect SQL evidence to AX process context when the data allows it. If the mapping is inferred rather than proven, say so explicitly.

## Required Inputs

- SQL Server time window, instance, database, and AX environment name.
- Top queries by CPU, reads, writes, duration, and execution count.
- Wait stats deltas, blocking/deadlock evidence, TempDB usage, and database file latency.
- AX batch history, AOS events or counters, user/session load, and long-running AX query evidence.
- Trace Parser or DynamicsPerf exports when available.
- Business calendar context such as month-end close, inventory close, MRP, retail statement posting, integrations, reporting, backups, and maintenance windows.
- Recent deployment, configuration, index/statistics maintenance, or infrastructure change timestamps.
- Table growth, data-retention, archive, and cleanup context where available.
- Environment comparison data for production, pre-production, test, and disaster recovery where non-reproducibility matters.
- Ownership mapping for modules, custom objects, integrations, support queues, and vendors where available.

## Workflow

1. Establish the time window and business impact.
2. Identify the top SQL pressure points: CPU, reads, duration, waits, blocking, and I/O latency.
3. Map SQL objects to AX tables and known high-risk areas such as InventTrans, CustTrans, VendTrans, SalesLine, PurchLine, and GeneralJournalAccountEntry.
4. Correlate SQL spikes with AX batch jobs, AOS load, services, retail sync, or user activity.
5. Check the AX anti-pattern library: broad scans, missing company/partition selectivity, parameter-sensitive plans, batch collisions, repeated short SQL calls, TempDB spikes, and recurring blocking roots.
6. Classify each finding by severity, confidence, business impact, change-readiness risk, reversibility, and expected operational benefit.
7. Check whether the finding is recurring performance debt, an SLA breach risk, a deployment regression, a data-growth issue, or an environment drift issue.
8. Decide whether the issue is tune-now, redesign-needed, migration-signal, archive-candidate, capacity-planning-signal, or custom-code-hotspot.
9. Produce recommendations that are advisory only unless the user explicitly asks for implementation scripts.

## AX Knowledge Base Targets

Pay special attention to:

- Inventory: `InventTrans`, `InventSum`, `InventDim`, inventory close, recalculation, master planning.
- Finance: `CustTrans`, `VendTrans`, `LedgerJournalTrans`, `GeneralJournalAccountEntry`, settlement, posting, month-end close.
- Trade: `SalesTable`, `SalesLine`, `PurchTable`, `PurchLine`, picking, packing, invoicing.
- Batch: `Batch`, `BatchJob`, `BatchHistory`, SysOperation classes, batch groups, AOS assignment.
- Retail and integrations: retail transaction tables, statement posting, AIF services, EDI imports, recurring exports.
- Customization: custom tables, custom classes, reports, services, forms, event handlers, and integration code visible through Trace Parser, DynamicsPerf, SQL object names, or deployment history.
- Data lifecycle: staging tables, logs, workflow history, batch history, retail history, old transactions, and closed documents that may be archive or cleanup candidates.

## Additional Analysis Dimensions

- Performance debt: repeated findings, finding age, deferment reason, owner, and next decision.
- SLA prediction: runtime trend, data-growth trend, wait trend, and likely breach horizon.
- Deployment regression: baseline vs. post-change change in duration, CPU, reads, waits, and blocking.
- Environment drift: production-only SQL settings, index/statistics differences, data volume, AOS configuration, and batch setup.
- Ownership routing: business owner, technical owner, support queue, vendor, or customization owner.
- Role/user impact: user sessions, affected roles, affected departments, and company-specific impact.

## Recommendation Format

Each finding must include:

- Observation: metric, threshold, and time window.
- Evidence: source DMV/export/counter and query or object identifier.
- AX context: affected table, class, batch job, AOS, service, or module when known.
- Likely cause: for example stale statistics, missing composite index, parameter sniffing, blocking chain, TempDB pressure, or batch collision.
- Recommended action: concrete next step with human approval.
- Change readiness: technical risk, AX compatibility, regression-test effort, downtime risk, rollback complexity, and approval path.
- Validation: before/after metric, observation period, success threshold, and rollback note.
- Audit note: source evidence, analysis timestamp, and whether the recommendation is fact, inference, or assumption.
- Debt and forecast: recurrence, age, SLA breach horizon, and cost of deferral when evidence supports it.
- Ownership: responsible team or unknown-owner flag.
- Playbook: diagnostic path and recommended remediation pattern.

## Output Modes

- Daily health check: concise status, risk trend, and urgent actions.
- Technical analysis: detailed findings with evidence and validation queries.
- Change impact analysis: baseline vs. post-change comparison with improvement or regression statement.
- Executive summary: health score, top risks, business impact, and decision requests.
- Performance debt register: recurring open findings with owners and next decisions.
- SLA forecast: likely breaches and capacity warnings.
- Environment drift report: production/test/pre-production differences relevant to performance.
