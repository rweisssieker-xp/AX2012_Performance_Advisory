---
name: management-report-generator
description: Generate executive and change-control reports for AX 2012 performance findings with risk, impact, evidence, recommendations, and audit-ready action plans.
---

# Management Report Generator

Use this skill to turn technical AX/SQL performance findings into management summaries, change proposals, and regulated-environment documentation.

## Report Structure

- Executive summary: health score, top risks, business impact, and recommended decision.
- Top findings: ranked by impact, urgency, confidence, and implementation risk.
- Evidence summary: data sources, time windows, and measurement limitations.
- Action plan: owner, effort, risk, expected effect, validation metric, rollback option, and change category.
- Before/after section: baseline, post-change result, measured delta, and conclusion.
- Migration signal section: issues that are symptoms of structural legacy constraints rather than isolated tuning problems.
- Appendix: detailed SQL/AX evidence for technical reviewers.

## Executive Metrics

Use these metrics when evidence exists:

- Overall performance score.
- Number of critical/high findings.
- Batch SLA adherence.
- Top wait categories.
- Top business processes at risk.
- Change backlog by risk and effort.
- Improvement after implemented changes.
- Deferred-risk statement for unresolved findings.

## Tone

Use clear business language. Avoid hiding uncertainty. Distinguish observed facts, likely causes, and recommendations.

## GxP / ITIL Considerations

- State that recommendations are advisory and require approval before implementation.
- Include audit trail references to the source exports and analysis timestamp.
- For each change, include risk assessment, test evidence needed, rollback guidance, and post-change monitoring criteria.
- Separate low-risk operational changes from validated changes requiring CAB, QA, or business-process owner approval.
- Preserve uncertainty: use "observed", "correlates with", "likely", and "requires validation" accurately.

## Finding Narrative Template

Use this structure for each management-facing finding:

- What happened.
- Why it matters.
- Evidence behind the conclusion.
- Recommended decision.
- Risk if deferred.
- Risk if implemented.
- Validation and rollback.
