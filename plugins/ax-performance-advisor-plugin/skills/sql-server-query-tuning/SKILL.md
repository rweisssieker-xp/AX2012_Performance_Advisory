---
name: sql-server-query-tuning
description: Interpret SQL Server 2016 performance evidence for Dynamics AX 2012 workloads, including expensive queries, waits, indexes, statistics, plan cache, Query Store, and parameter sniffing.
---

# SQL Server Query Tuning For AX

Use this skill when reviewing SQL Server 2016 data from AX 2012 R3 systems.

## Evidence To Review

- `sys.dm_exec_query_stats`, execution plans, and query text.
- Wait stats deltas, especially PAGEIOLATCH, CXPACKET/CXCONSUMER, LCK, WRITELOG, RESOURCE_SEMAPHORE, and TEMPDB-related waits.
- Missing index DMVs, index usage, index operational stats, fragmentation, and statistics age.
- Blocking chains, deadlock graphs, Query Store data if enabled, and file I/O latency.
- Table row counts, reserved/used space, index size, partition/company distribution, and historical growth where available.
- Production vs. test/pre-production differences in database options, indexes, statistics, compatibility level, maintenance jobs, and data volume.

## AX-Specific Guardrails

- Do not recommend broad or speculative index changes on large AX transaction tables.
- Consider DataAreaId, Partition, RecId, and common AX join/filter patterns before suggesting index keys.
- Prefer evidence-backed statistics updates, targeted index review, query pattern validation, and batch scheduling adjustments before invasive changes.
- Flag changes requiring AX model/store deployment, downtime, regression testing, or formal change approval.
- Treat missing-index DMV output as a signal, not a recommendation. Validate against existing AX indexes, write overhead, table size, update frequency, and query recurrence.
- Do not frame `NOLOCK`, forced plans, MAXDOP changes, or trace flags as casual fixes. They require explicit risk analysis and validation.

## Parameter-Sniffing Signals

Look for:

- Same query hash with strongly different duration, reads, CPU, or memory grant.
- Multiple plans for related text or query hash.
- Runtime variance linked to company, item, customer, date range, or status distribution.
- Intermittent regressions after statistics updates, deployments, or plan cache eviction.

Recommended response:

- First confirm recurrence and business impact.
- Compare plans and parameter values where available.
- Suggest targeted plan/query review, statistics strategy, or code-level query shape review before server-wide changes.

## Index And Statistics Advice

When proposing index or statistics work, include:

- Existing index coverage and usage.
- Candidate key order and included columns.
- AX fields involved, especially `Partition`, `DataAreaId`, status/date fields, dimensions, and `RecId`.
- Write overhead and maintenance cost.
- Deployment path, test plan, and rollback.
- Before/after metrics: logical reads, CPU, duration, wait profile, blocking, and write cost.

## Data Growth And Archive Signals

Flag growth-driven findings when:

- Runtime grows with table row count or index size.
- Maintenance, backup, or statistics windows are expanding.
- Old closed records dominate a high-cost table.
- Staging, log, workflow, retail, or integration tables grow without retention.
- Query tuning would only defer the underlying data-lifecycle problem.

Archive recommendations must include business approval, retention/audit risk, reporting impact, validation, and rollback or restore approach.

## Environment Drift Checks

When a problem is production-only, compare:

- Database options and compatibility level.
- Max degree of parallelism and cost threshold settings where available.
- Index definitions and disabled/hypothetical indexes.
- Statistics age, sample rate, and auto-update behavior.
- Data volume and distribution by company/module/date.
- Maintenance schedule and Query Store availability.

## Output

For each SQL finding, provide the query signature, affected database object, AX table mapping if known, observed metric, suspected cause, recommendation, change-readiness score, validation query, rollback note, data-growth signal, and environment-drift signal.
