# AI/KI Feature Pack

The AI/KI layer is implemented as a local deterministic advisory engine in `scripts/ai_insights.py`. It does not require external LLM access. It uses normalized AXPA findings, severity, confidence, evidence, AX context, SQL context, change readiness, and validation metadata to create explainable advisory artifacts.

## Run

```powershell
python .\scripts\ai_insights.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\IT-TEST-ERP4CU-ai-insights.json `
  --markdown-output .\out\IT-TEST-ERP4CU-ai-insights.md `
  --question "Warum war AX langsam?"
```

The same feature is exposed through MCP as `generate_ai_insights`.

## Implemented Features

| Feature | Output key | What it does |
| --- | --- | --- |
| Natural Language Root Cause Chat | `naturalLanguageRootCauseChat` | Answers an operator question from top evidence-backed findings. |
| AI Finding Explainer | `findingExplainers` | Explains findings for technical, key-user, and management audiences. |
| AI Change Risk Predictor | `changeRiskPredictor` | Scores remediation risk from severity, approval, test effort, rollback, and AX compatibility. |
| AI Batch Scheduler Optimizer | `batchSchedulerOptimizer` | Extracts batch-related findings and proposes safer sequencing/validation. |
| AI Query-to-AX-Code Mapping | `queryToAxCodeMapping` | Maps SQL query evidence to AX tables and candidate X++ attribution evidence. |
| AI Regression Detector | `regressionDetector` | Converts regression evidence or candidates into before/after checks. |
| AI Remediation Planner | `remediationPlanner` | Groups work into phased low-risk, TEST, and CAB-ready remediation waves. |
| AI Evidence Gap Detector | `evidenceGapDetector` | Finds missing evidence such as Trace Parser, Query Store, deadlock, batch, or session evidence. |
| AI Incident Summary | `incidentSummary` | Produces an incident summary with severity mix, modules, playbooks, and next action. |
| AI GxP Validation Assistant | `gxpValidationAssistant` | Drafts test objective, expected result, deviation handling, approval path, and rollback. |
| AI Runbook Copilot | `runbookCopilot` | Produces operator steps for the highest-priority findings. |
| AI Noise Reduction | `noiseReduction` | Deduplicates findings into actionable groups by playbook, module, and objects. |
| AI Business Impact Estimator | `businessImpactEstimator` | Converts technical findings into module, owner, and risk language. |
| AI Knowledge Base Learning | `knowledgeBaseLearning` | Turns recurring findings into candidate learning rules. |
| AI Anomaly Forecasting | `anomalyForecasting` | Identifies trend-backed or trend-missing forecast candidates. |
| AI D365 Migration Signal | `d365MigrationSignal` | Separates tune-now issues from modernization/data-platform signals. |
| AI Ticket Auto-Drafting | `ticketAutoDrafting` | Drafts ticket fields with acceptance criteria, rollback, owner, and labels. |
| AI Executive Narrative | `executiveNarrative` | Produces CIO-ready risk narrative and board ask. |
| AI SQL Plan Interpreter | `sqlPlanInterpreter` | Interprets plan/query findings and points to plan XML parsing when available. |
| AI Safe Action Classifier | `safeActionClassifier` | Classifies actions as observe, maintenance-window, TEST-only, CAB-required, or review-required. |

## Safety

- Advisory only by default.
- No automatic SQL, AX, schema, or configuration changes.
- Every high-risk action remains TEST/CAB gated.
- Missing evidence is surfaced explicitly instead of hidden.
