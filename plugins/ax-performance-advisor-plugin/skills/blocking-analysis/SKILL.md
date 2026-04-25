---
name: blocking-analysis
description: Analyze SQL blocking, deadlocks, lock waits, root blockers, affected AX tables, and recommended low-risk remediation.
---

# Blocking Analysis

Use this skill when evidence includes `blocking.csv`, `deadlock_processes.csv`, lock waits, or deadlock XML.

## Workflow

1. Parse deadlock XML with `scripts/parse_deadlock_xml.py` when needed.
2. Analyze lock waits and blocking findings with `scripts/analyze_evidence.py`.
3. Map blocked objects to AX tables and owners.
4. Recommend schedule separation, transaction-scope review, or targeted code/query review.

## Guardrail

Do not recommend isolation-level or `NOLOCK` changes casually. Require risk and validation notes.

