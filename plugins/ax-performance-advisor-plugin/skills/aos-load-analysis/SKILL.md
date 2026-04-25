---
name: aos-load-analysis
description: Analyze AOS counters, user sessions, batch/service distribution, AOS topology, and load-separation recommendations.
---

# AOS Load Analysis

Use this skill when AOS counters, sessions, or topology are relevant.

## Workflow

1. Collect counters with `scripts/collect_aos_counters.ps1`.
2. Review `aos_counters.csv`, `user_sessions.csv`, and batch AOS assignment.
3. Run `scripts/aos_topology_advisor.py`.
4. Recommend batch/service/user separation where evidence supports it.

