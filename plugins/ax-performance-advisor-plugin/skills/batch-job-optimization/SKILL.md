---
name: batch-job-optimization
description: Analyze Dynamics AX 2012 batch jobs, SysOperation workloads, collisions, runtime trends, and SQL side effects to recommend safer scheduling and tuning actions.
---

# Batch Job Optimization

Use this skill when AX batch runtime, nightly processing, retail jobs, AIF/services, or SysOperation workloads are suspected performance drivers.

## Inputs

- Batch job and task history with start time, end time, status, company, class, and AOS.
- SQL wait/query/blocking evidence for the same time window.
- AOS event logs, performance counters, and user session patterns.
- Deployment or configuration change timestamps for before/after comparison.
- Historical runtime trends, SLA targets, and maintenance-window boundaries.
- Batch-group and AOS assignment across environments where environment drift is suspected.

## Analysis

1. Find long-running jobs, retry patterns, failures, and runtime variance.
2. Detect overlapping high-load jobs and collisions with user activity, integrations, or maintenance.
3. Correlate batch windows with SQL waits, blocking, top queries, TempDB pressure, and file latency.
4. Compare normal days with business-critical windows such as month-end close, inventory close, MRP, statement posting, and EDI imports.
5. Forecast whether job duration will breach the target window based on recent trends.
6. Identify performance debt: recurring jobs whose findings are repeatedly deferred.
7. Separate tuning actions into scheduling, parallelism, AX code/query review, SQL maintenance, data lifecycle, and infrastructure capacity.

## Collision Patterns

Flag these patterns explicitly:

- Multiple heavy jobs using the same table family in the same window.
- Batch jobs overlapping with index/statistics maintenance, backups, ETL, or reporting.
- Long-running jobs assigned to an overloaded AOS while other AOS nodes are idle.
- Frequent retries or partial failures that increase total load.
- Jobs with rising duration trend after deployments or data-volume growth.
- Posting, settlement, inventory, retail, or integration jobs causing repeat blocking roots.
- Jobs that fit in test but fail in production due to data volume, AOS assignment, or schedule drift.
- Custom batch classes whose SQL signature or Trace Parser stack dominates the runtime.

## Recommendations

Prefer low-risk operational changes first: reschedule conflicting jobs, split oversized workloads, adjust batch groups or AOS assignment, and validate maintenance windows. Escalate to SQL or X++ changes only when evidence supports it.

Each recommendation must include expected effect, affected business process, operational risk, validation window, owner, and rollback path. For GxP environments, describe the change as a proposal requiring approval, not an instruction to execute.

## SLA Forecast Output

When trend data exists, include:

- Current average runtime and p95 runtime.
- Weekly or monthly growth rate.
- Target window and remaining buffer.
- Predicted breach horizon.
- Confidence and data limitations.
- Recommended decision date.
