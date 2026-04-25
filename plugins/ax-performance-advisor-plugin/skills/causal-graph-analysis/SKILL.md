---
name: causal-graph-analysis
description: Analyze AX performance as a cause-effect graph linking root causes, waits, findings, tables, and business impact.
---

# Causal Graph Analysis

Use this skill when a finding list is too flat and the user needs cause-effect explanation.

## Workflow

1. Run `scripts/build_causal_graph.py`.
2. Traverse root-cause nodes to waits, findings, and AX tables.
3. Use `scripts/root_cause_narrative.py` for a readable narrative.

