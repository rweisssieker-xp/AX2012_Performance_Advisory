---
name: daily-health-check
description: Run a daily AX 2012 and SQL Server health check with prioritized risks, module health scores, root causes, and management summary.
---

# Daily Health Check

Use this skill to summarize the current AX performance posture from an evidence directory.

## Workflow

1. Run `scripts/analyze_evidence.py`.
2. Run `scripts/generate_report.py` and optionally `scripts/generate_html_report.py`.
3. Review module health scores, top root causes, high/critical findings, and performance debt.
4. Produce a concise decision list: immediate, next maintenance window, observe, architecture topic.

## Related Scripts

- `analyze_evidence.py`
- `generate_report.py`
- `generate_html_report.py`
- `auto_triage.py`
- `score_root_cause_confidence.py`

