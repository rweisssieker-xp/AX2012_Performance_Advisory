# Autonomous Ops

Autonomous Ops extends AX Performance Advisor from static diagnosis into controlled operational planning. It does not execute production changes. It turns existing AXPA evidence into investigation queues, follow-up questions, read-only collector commands, change drafts, validation plans, readiness gates, and executive risk briefings.

## Real behavior

- Uses `analyze_evidence()` output and the current evidence bundle.
- Emits read-only collection commands for SQL, AX DB, AOS counters, Trace Parser imports, and DynamicsPerf imports.
- Marks missing sources explicitly instead of inventing data.
- Classifies findings as `ready-for-test`, `requires-approval`, or `needs-more-evidence`.
- Generates CAB/GxP-friendly change drafts with test and rollback notes.
- Keeps admin execution separate from advice and planning.

## Outputs

- `investigationQueue`
- `followUpQuestions`
- `evidenceAcquisitionPlanner`
- `changeDrafts`
- `validationRunPlanner`
- `readinessGate`
- `operatorDecisionMemory`
- `nextBestActions`
- `executiveRiskBriefing`
- `safeToAutomateClassifier`
- `postChangeEvidenceChecklist`
- `falsePositiveSuppression`
- `businessImpactReframing`
- `adminApprovalReadinessGate`
- `rootCauseDecisionTree`
- `hypothesisConfidenceTimeline`
- `findingToQuestionCopilot`
- `rollbackReadinessScore`
- `recommendationAcceptanceLearning`

## CLI

```powershell
python .\scripts\autonomous_ops.py --evidence .\evidence\IT-TEST-ERP4CU --output .\out\autonomous-ops.json
python .\scripts\generate_dashboard.py --evidence .\evidence\IT-TEST-ERP4CU --output .\out\IT-TEST-ERP4CU-dashboard.html
```
