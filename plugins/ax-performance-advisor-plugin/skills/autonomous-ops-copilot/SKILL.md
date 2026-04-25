---
name: autonomous-ops-copilot
description: Build or run Autonomous Ops workflows for AX Performance Advisor, including investigation queues, evidence acquisition plans, follow-up questions, change drafts, validation planning, and readiness gates.
---

# Autonomous Ops Copilot

Use this skill when the user wants AXPA to move from analysis into controlled operational planning without directly changing production systems.

## Workflow

1. Generate the Autonomous Ops pack with `scripts/autonomous_ops.py`.
2. Review `evidenceAcquisitionPlanner` first; missing evidence must be collected or explicitly accepted as a limitation.
3. Use `investigationQueue` and `rootCauseDecisionTree` to decide the next diagnostic step.
4. Use `changeDrafts` and `validationRunPlanner` only for findings with enough evidence and an owner.
5. Keep admin execution gated by approval, rollback, validation evidence, and a confirmation token.

## Safety

- Treat every generated command as read-only unless explicitly reviewed by an admin.
- Do not create indexes, alter SQL configuration, update AX data, or change batch schedules from this skill.
- If Trace Parser, DynamicsPerf, or plan XML evidence is missing, state that X++ attribution is evidence-gated.
