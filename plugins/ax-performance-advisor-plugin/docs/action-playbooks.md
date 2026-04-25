# Action Playbooks

Action playbooks translate recurring finding types into a consistent diagnostic and change-control path.

## Playbook Template

- Trigger: evidence pattern that activates the playbook.
- Confirm: additional checks needed before recommending action.
- Low-risk actions: operational or reversible steps.
- Change proposal: implementation option requiring approval.
- Validation: success metrics and observation window.
- Rollback: specific reversal or fallback.
- Risks: AX, SQL, business, compliance, and downtime concerns.

## Initial Playbooks

### Stale Statistics

- Trigger: high-cost query regression, stale modification counters, changed cardinality, or plan instability.
- Confirm: table size, update pattern, current statistics date/sample, and affected query plan.
- Low-risk actions: targeted statistics update in approved window.
- Validation: compare reads, CPU, duration, and plan shape.

### Blocking Chain

- Trigger: repeated LCK waits, blocked process reports, deadlock graphs, or batch/user complaints.
- Confirm: root blocker, AX process, transaction duration, isolation behavior, and time window.
- Low-risk actions: reschedule conflicting jobs, reduce overlap, review transaction scope.
- Validation: blocking duration and recurrence.

### Batch Collision

- Trigger: overlapping heavy jobs, rising runtime, shared table pressure, or SQL wait spikes.
- Confirm: batch groups, AOS assignment, maintenance collisions, and business window.
- Low-risk actions: sequence jobs, split workload, adjust batch groups.
- Validation: p95 runtime, wait profile, and SLA buffer.

### Parameter-Sensitive Plan

- Trigger: same query with high runtime variance or multiple plan shapes.
- Confirm: parameter distribution, company/date/item skew, plan cache behavior, and recurrence.
- Low-risk actions: targeted query/code review and statistics validation.
- Validation: variance reduction and plan stability.

### Missing Composite Index Candidate

- Trigger: repeated high logical reads with stable predicate pattern and missing-index signal.
- Confirm: existing index overlap, write cost, AX keys, table volume, and recurrence.
- Low-risk actions: review candidate index with AX/DBA owner.
- Validation: reads, CPU, duration, writes, and maintenance cost.

### TempDB Pressure

- Trigger: TempDB waits, file growth, spills, version store growth, or allocation contention.
- Confirm: top spilling queries, batch/report overlap, file layout, and workload timing.
- Low-risk actions: reschedule pressure, review queries, validate TempDB configuration.
- Validation: spill count, TempDB waits, file growth, and job runtime.

### Data Growth

- Trigger: runtime and maintenance cost rising with row count or index size.
- Confirm: table growth by date/company/module, closed-record volume, reporting needs, and retention rules.
- Low-risk actions: retention/archive assessment and cleanup candidate review.
- Validation: row count, index size, runtime, backup, and maintenance duration.

### Deployment Regression

- Trigger: metric degradation after deployment, hotfix, index, configuration, or infrastructure change.
- Confirm: comparable baseline, changed objects, data volume, and workload similarity.
- Low-risk actions: isolate changed component and prepare rollback or fix proposal.
- Validation: before/after comparison after correction.

### Environment Drift

- Trigger: problem reproducible in production but not test/pre-production.
- Confirm: settings, data volume, indexes, statistics, AOS setup, batch schedule, and maintenance differences.
- Low-risk actions: align test evidence or document production-only cause.
- Validation: reproduced issue or accepted drift explanation.
