---
name: knowledge-base-governance
description: Maintain known issues, self-healing rules, feedback loops, and anonymized AX performance pattern libraries.
---

# Knowledge Base Governance

Use this skill after findings are validated, resolved, rejected, or converted into reusable rules.

## Workflow

1. Run `scripts/capture_knowledge_feedback.py`.
2. Run `scripts/update_self_healing_rules.py`.
3. Run `scripts/export_anonymized_patterns.py`.
4. Match future findings with `scripts/match_known_issues.py`.

