---
name: change-blast-radius-analysis
description: Analyze which AX modules, tables, findings, owners, and processes may be affected by a planned change.
---

# Change Blast Radius Analysis

Use this skill before approving index, statistics, archive, batch, X++ or infrastructure changes.

## Workflow

1. Run `scripts/change_blast_radius.py --target <object>`.
2. Review affected findings, modules, and owners.
3. Feed the result into CAB package and remediation portfolio.

