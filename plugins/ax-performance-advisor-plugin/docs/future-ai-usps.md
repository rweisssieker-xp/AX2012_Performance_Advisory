# Future AI/KI USP Backlog

The following ideas are not required for the current MVP, but would create additional differentiation.

## USP 92: Interactive Evidence Q&A With Source Drilldown

Let operators ask free-form questions and receive answers with links to exact findings, evidence rows, reports, and collector errors. This requires an LLM/RAG layer or a local semantic index.

## USP 93: AX Code Remediation Diff Assistant

When Trace Parser or DynamicsPerf maps a slow SQL pattern to custom X++ code, generate a proposed code-review checklist or candidate refactor diff for developers.

## USP 94: Dynamic Business SLA Contract Builder

Infer candidate SLOs for batch jobs, close tasks, integrations, and reports from historical evidence, then let owners approve them as versioned performance contracts.

## USP 95: Change Outcome Learning

Persist whether approved recommendations improved, regressed, or had no measurable effect. Use those outcomes to adjust future confidence and risk scoring.

## USP 96: Synthetic Load Replay Planner

Generate a TEST replay plan from production evidence: representative query families, batch windows, data volumes, and success criteria.

## USP 97: Architecture Smell Detector

Identify structural AX anti-patterns such as reporting on OLTP tables, custom integrations using row-by-row inserts, overloaded batch groups, and missing data lifecycle ownership.

## USP 98: Role-Based Briefing Generator

Generate separate briefings for DBA, AX developer, operations, process owner, QA/GxP, and CIO from the same findings.

## USP 99: Evidence Trust Score

Score every analysis run for completeness, freshness, collector health, source diversity, and reproducibility. Use the score to prevent overconfident recommendations.

## USP 100: Closed-Loop Change Governance

Track each finding from detection through approval, implementation, validation, and closure, including evidence hashes and sign-off metadata.

## USP 101: SQL 2016 End-of-Support Risk Advisor

Combine SQL Server 2016 lifecycle exposure with current performance debt and modernization signals to produce a risk-based upgrade/migration briefing.

## USP 102: Cross-System Dependency Map

Map AIF, EDI, SSIS, reporting, SQL Agent, retail, and external integrations around AX batch windows to explain upstream/downstream performance impact.

## USP 103: Autonomous Collector Fix Suggestions

When a collector produces `.error.csv`, generate the likely permission/schema/timeout cause and a minimal read-only fix proposal.
