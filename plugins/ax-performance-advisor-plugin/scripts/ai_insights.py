from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, module_health_scores, summarize_root_causes, write_json
from realization_pack import generate_realization_pack


SEVERITY_POINTS = {"critical": 5, "high": 4, "medium": 2, "low": 1, "informational": 0}


AI_FEATURES = [
    "natural-language-root-cause-chat",
    "ai-finding-explainer",
    "ai-change-risk-predictor",
    "ai-batch-scheduler-optimizer",
    "ai-query-to-ax-code-mapping",
    "ai-regression-detector",
    "ai-remediation-planner",
    "ai-evidence-gap-detector",
    "ai-incident-summary",
    "ai-gxp-validation-assistant",
    "ai-runbook-copilot",
    "ai-noise-reduction",
    "ai-business-impact-estimator",
    "ai-knowledge-base-learning",
    "ai-anomaly-forecasting",
    "ai-d365-migration-signal",
    "ai-ticket-auto-drafting",
    "ai-executive-narrative",
    "ai-sql-plan-interpreter",
    "ai-safe-action-classifier",
]


def _severity_rank(finding: dict[str, Any]) -> int:
    return SEVERITY_POINTS.get(str(finding.get("severity", "low")).lower(), 0)


def _top(findings: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: (_severity_rank(f), len(f.get("evidence", []))), reverse=True)[:limit]


def _finding_text(finding: dict[str, Any]) -> str:
    module = finding.get("axContext", {}).get("module", "Unknown")
    playbook = finding.get("recommendation", {}).get("playbook", "review")
    return f"{finding.get('severity', 'unknown').upper()}: {finding.get('title', '')} ({module}, {playbook})"


def _objects(finding: dict[str, Any]) -> list[str]:
    ax = finding.get("axContext", {})
    sql = finding.get("sqlContext", {})
    values = []
    for key in ("tables", "batchJobs", "classes", "aos", "companies"):
        values.extend(ax.get(key, []) or [])
    values.extend(sql.get("objects", []) or [])
    values.extend(sql.get("waitTypes", []) or [])
    return sorted({str(v) for v in values if v})


def _risk_bucket(finding: dict[str, Any]) -> str:
    approval = finding.get("recommendation", {}).get("requiresApproval", True)
    risk = finding.get("changeReadiness", {})
    if finding.get("severity") in {"critical", "high"} and approval:
        return "CAB-required"
    if risk.get("technicalRisk") == "high" or risk.get("axCompatibilityRisk") == "high":
        return "TEST-only"
    if finding.get("confidence") == "low":
        return "observe"
    if finding.get("severity") in {"medium", "low"}:
        return "maintenance-window"
    return "review-required"


def _evidence_grade(finding: dict[str, Any]) -> str:
    evidence_count = len(finding.get("evidence", []))
    confidence = finding.get("confidence", "low")
    if confidence == "high" and evidence_count >= 2:
        return "A"
    if confidence in {"high", "medium"} and evidence_count >= 1:
        return "B"
    if evidence_count >= 1:
        return "C"
    return "D"


def generate_ai_insights(evidence: str | Path, question: str = "") -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    top_findings = _top(findings, 12)
    root_causes = summarize_root_causes(findings)
    module_scores = module_health_scores(findings)
    severity_counts = Counter(f.get("severity", "unknown") for f in findings)
    playbook_counts = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    module_counts = Counter(f.get("axContext", {}).get("module", "Unknown") for f in findings)

    grouped_by_playbook: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped_by_playbook[finding.get("recommendation", {}).get("playbook", "review")].append(finding)

    query_findings = [f for f in findings if f.get("sqlContext", {}).get("queryHash") or "query" in f.get("title", "").lower()]
    batch_findings = [f for f in findings if f.get("axContext", {}).get("batchJobs") or "batch" in f.get("title", "").lower()]
    regression_findings = [f for f in findings if "regression" in json.dumps(f.get("regression", {})).lower() or "regression" in f.get("title", "").lower()]
    migration_findings = [f for f in findings if f.get("classification") in {"migration-signal", "redesign-needed"} or f.get("dataGrowth", {}).get("isGrowthDriven")]
    plan_findings = [f for f in findings if "plan" in f.get("title", "").lower() or f.get("sqlContext", {}).get("planHash")]

    action_sequence = []
    for playbook, items in playbook_counts.most_common(8):
        sample = grouped_by_playbook[playbook][0]
        action_sequence.append(
            {
                "playbook": playbook,
                "findingCount": len(grouped_by_playbook[playbook]),
                "priority": sample.get("severity", "medium"),
                "firstAction": sample.get("recommendation", {}).get("summary", "Review grouped evidence."),
                "validation": sample.get("validation", {}).get("successMetric", "Compare before/after evidence."),
                "owner": sample.get("recommendation", {}).get("owner", "AX Operations"),
            }
        )

    evidence_gaps = []
    required_sources = {
        "deadlocks": "Deadlock XML or deadlock CSV evidence for blocking root-cause proof.",
        "trace": "Trace Parser or DynamicsPerf export for SQL-to-X++ attribution.",
        "batch": "AX batch history for schedule optimization.",
        "query_store": "Query Store runtime for regression and plan stability proof.",
        "sessions": "AX user/session evidence for user-impact correlation.",
    }
    evidence_path = Path(evidence)
    file_names = {p.name.lower() for p in evidence_path.glob("*")} if evidence_path.exists() else set()
    for key, text in required_sources.items():
        if not any(key in name for name in file_names):
            evidence_gaps.append({"source": key, "reason": text, "nextCollection": "Collect read-only evidence in the affected time window."})

    noise_reduced = []
    seen = set()
    for finding in _top(findings, len(findings)):
        signature = (
            finding.get("classification"),
            finding.get("recommendation", {}).get("playbook"),
            finding.get("axContext", {}).get("module"),
            tuple(_objects(finding)[:3]),
        )
        if signature in seen:
            continue
        seen.add(signature)
        noise_reduced.append(finding)

    safe_actions = [
        {
            "findingId": f.get("id"),
            "title": f.get("title"),
            "classification": _risk_bucket(f),
            "why": f"{f.get('severity')} severity, {f.get('confidence')} confidence, approval={f.get('recommendation', {}).get('requiresApproval', True)}",
            "nextStep": f.get("recommendation", {}).get("summary", "Review evidence."),
        }
        for f in top_findings
    ]

    explainers = [
        {
            "findingId": f.get("id"),
            "title": f.get("title"),
            "technical": f"{f.get('likelyCause', '')} Evidence: {', '.join([str(e.get('source', '')) for e in f.get('evidence', [])[:3]])}.",
            "keyUser": f"Betroffener Bereich: {f.get('axContext', {}).get('module', 'Unknown')}. Erwartete Wirkung: {f.get('businessImpact', {}).get('impact', 'Performance risk reduction')}.",
            "management": f"{f.get('severity', 'unknown').upper()} Risiko mit {f.get('confidence', 'unknown')} Confidence. Empfohlene Freigabe: {f.get('changeReadiness', {}).get('approvalPath', 'Review')}.",
        }
        for f in top_findings[:10]
    ]

    ticket_drafts = [
        {
            "title": f"{f.get('id')} {f.get('title')}",
            "type": "Risk" if f.get("severity") in {"critical", "high"} else "Task",
            "priority": f.get("severity"),
            "description": f.get("recommendation", {}).get("summary", ""),
            "acceptanceCriteria": f.get("validation", {}).get("successMetric", ""),
            "rollback": f.get("validation", {}).get("rollback", ""),
            "owner": f.get("axContext", {}).get("technicalOwner", "AX Operations"),
            "labels": ["AXPA", f.get("classification", "review"), f.get("recommendation", {}).get("playbook", "review")],
        }
        for f in top_findings
    ]

    result = {
        "metadata": {
            "featureCount": len(AI_FEATURES),
            "features": AI_FEATURES,
            "mode": "local-deterministic-advisory",
            "evidence": str(evidence),
            "findingCount": len(findings),
        },
        "naturalLanguageRootCauseChat": {
            "question": question or "Warum ist AX langsam?",
            "answer": "Die staerksten aktuellen Signale sind: "
            + "; ".join(_finding_text(f) for f in top_findings[:5])
            + ". Diese Antwort basiert auf den normalisierten AXPA-Findings und ist als Diagnose-Hypothese mit Evidence zu lesen.",
            "supportingFindingIds": [f.get("id") for f in top_findings[:5]],
        },
        "findingExplainers": explainers,
        "changeRiskPredictor": [
            {
                "findingId": f.get("id"),
                "riskClass": _risk_bucket(f),
                "technicalRisk": f.get("changeReadiness", {}).get("technicalRisk", "medium"),
                "axCompatibilityRisk": f.get("changeReadiness", {}).get("axCompatibilityRisk", "medium"),
                "rollbackComplexity": f.get("changeReadiness", {}).get("rollbackComplexity", "medium"),
                "testEffort": f.get("changeReadiness", {}).get("testEffort", "medium"),
            }
            for f in top_findings
        ],
        "batchSchedulerOptimizer": {
            "findingCount": len(batch_findings),
            "recommendations": [
                {
                    "findingId": f.get("id"),
                    "batchJobs": f.get("axContext", {}).get("batchJobs", []),
                    "proposal": "Separate this workload from high-read SQL windows and validate in TEST with comparable business data.",
                    "validation": f.get("validation", {}).get("successMetric", "Reduce overlap-related waits and duration."),
                }
                for f in _top(batch_findings, 8)
            ],
        },
        "queryToAxCodeMapping": [
            {
                "findingId": f.get("id"),
                "queryHash": f.get("sqlContext", {}).get("queryHash", ""),
                "planHash": f.get("sqlContext", {}).get("planHash", ""),
                "tables": f.get("axContext", {}).get("tables", []) or f.get("sqlContext", {}).get("objects", []),
                "candidateAxObjects": f.get("axContext", {}).get("classes", []) or ["Trace Parser/DynamicsPerf evidence required for exact X++ call stack"],
            }
            for f in _top(query_findings, 12)
        ],
        "regressionDetector": {
            "findingCount": len(regression_findings),
            "candidates": [
                {
                    "findingId": f.get("id"),
                    "status": f.get("regression", {}).get("status", "candidate"),
                    "baselineDelta": f.get("regression", {}).get("baselineDelta", ""),
                    "nextCheck": "Compare before/after evidence and Query Store runtime for the same query family.",
                }
                for f in _top(regression_findings or top_findings, 8)
            ],
        },
        "remediationPlanner": {
            "weeklyPlan": [
                {"week": 1, "focus": "Evidence cleanup and no/low-risk operational checks", "actions": action_sequence[:3]},
                {"week": 2, "focus": "TEST validation for medium-risk tuning candidates", "actions": action_sequence[3:6]},
                {"week": 3, "focus": "CAB-ready high-impact proposals and post-change validation", "actions": action_sequence[6:8]},
            ]
        },
        "evidenceGapDetector": evidence_gaps,
        "incidentSummary": {
            "headline": f"{severity_counts.get('critical', 0)} critical, {severity_counts.get('high', 0)} high, {severity_counts.get('medium', 0)} medium findings detected.",
            "topModules": [{"module": k, "findings": v} for k, v in module_counts.most_common(5)],
            "topPlaybooks": [{"playbook": k, "findings": v} for k, v in playbook_counts.most_common(5)],
            "recommendedNextStep": action_sequence[0]["firstAction"] if action_sequence else "No action required.",
        },
        "gxpValidationAssistant": [
            {
                "findingId": f.get("id"),
                "testObjective": f.get("validation", {}).get("successMetric", "Validate measurable improvement."),
                "expectedResult": "Post-change evidence improves or remains within agreed threshold without new high-risk regressions.",
                "actualResult": "Pending execution.",
                "deviationHandling": "Document deviation, rollback if needed, and attach evidence pack.",
                "approvalPath": f.get("changeReadiness", {}).get("approvalPath", "CAB"),
            }
            for f in top_findings
        ],
        "runbookCopilot": [
            {
                "findingId": f.get("id"),
                "steps": [
                    "Confirm evidence timestamp and affected business window.",
                    f"Review objects: {', '.join(_objects(f)[:6]) or 'no direct object in evidence'}",
                    f"Execute playbook: {f.get('recommendation', {}).get('playbook', 'review')}",
                    f"Validate: {f.get('validation', {}).get('successMetric', 'before/after comparison')}",
                ],
            }
            for f in top_findings[:8]
        ],
        "noiseReduction": {
            "inputFindings": len(findings),
            "actionableGroups": len(noise_reduced),
            "topActionableFindingIds": [f.get("id") for f in noise_reduced[:20]],
        },
        "businessImpactEstimator": [
            {
                "findingId": f.get("id"),
                "module": f.get("axContext", {}).get("module", "Unknown"),
                "impact": f.get("businessImpact", {}).get("impact", ""),
                "estimatedBusinessRisk": "high" if f.get("severity") in {"critical", "high"} else "medium",
                "businessOwner": f.get("axContext", {}).get("businessOwner", "Unknown"),
            }
            for f in top_findings
        ],
        "knowledgeBaseLearning": [
            {
                "pattern": f.get("recommendation", {}).get("playbook", "review"),
                "matchSignals": _objects(f)[:8],
                "suggestedRule": f"Increase confidence for {f.get('recommendation', {}).get('playbook', 'review')} when the same signals recur with validated closure.",
                "status": "candidate-learning-case",
            }
            for f in top_findings[:10]
        ],
        "anomalyForecasting": {
            "riskTrend": "needs-trend-store" if not any("trend" in name.lower() for name in file_names) else "trend-evidence-present",
            "forecastCandidates": [
                {
                    "findingId": f.get("id"),
                    "signal": f.get("prediction", {}).get("capacitySignal", "") or f.get("title", ""),
                    "horizonDays": f.get("prediction", {}).get("slaBreachHorizonDays"),
                    "confidence": f.get("prediction", {}).get("trendConfidence", "unknown"),
                }
                for f in top_findings
            ],
        },
        "d365MigrationSignal": [
            {
                "findingId": f.get("id"),
                "signal": f.get("classification", ""),
                "reason": f.get("likelyCause", ""),
                "tables": f.get("axContext", {}).get("tables", []),
                "modernizationTheme": "data-lifecycle" if f.get("dataGrowth", {}).get("isGrowthDriven") else "customization-or-platform-pressure",
            }
            for f in _top(migration_findings or findings, 12)
        ],
        "ticketAutoDrafting": ticket_drafts,
        "executiveNarrative": {
            "summary": f"AXPA found {len(findings)} findings. The dominant risk areas are {', '.join([k for k, _ in playbook_counts.most_common(3)])}.",
            "riskMessage": "Prioritize high-severity findings with direct evidence, then reduce recurring medium-risk debt through approved maintenance windows.",
            "boardAsk": "Approve evidence-backed TEST validation and CAB preparation for the highest-impact findings.",
        },
        "sqlPlanInterpreter": [
            {
                "findingId": f.get("id"),
                "queryHash": f.get("sqlContext", {}).get("queryHash", ""),
                "planHash": f.get("sqlContext", {}).get("planHash", ""),
                "interpretation": f.get("likelyCause", "Review execution plan operators, estimates, spills, and index access pattern."),
                "nextCheck": "Use parse_plan_xml.py when an execution-plan XML file is available.",
            }
            for f in _top(plan_findings or query_findings or top_findings, 10)
        ],
        "safeActionClassifier": safe_actions,
        "moduleHealthScores": module_scores,
        "rootCauseGroups": root_causes,
        "realizationPack": generate_realization_pack(evidence),
    }
    return result


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# AI/KI Performance Advisory Pack",
        "",
        f"Mode: `{payload['metadata']['mode']}`",
        f"Findings: `{payload['metadata']['findingCount']}`",
        f"AI/KI Features: `{payload['metadata']['featureCount']}`",
        "",
        "## Root Cause Chat",
        "",
        payload["naturalLanguageRootCauseChat"]["answer"],
        "",
        "## Executive Narrative",
        "",
        payload["executiveNarrative"]["summary"],
        payload["executiveNarrative"]["riskMessage"],
        "",
        "## Safe Action Classes",
        "",
    ]
    for item in payload["safeActionClassifier"][:12]:
        lines.append(f"- `{item['classification']}`: {item['title']} ({item['findingId']})")
    lines.extend(["", "## Evidence Gaps", ""])
    for gap in payload["evidenceGapDetector"]:
        lines.append(f"- `{gap['source']}`: {gap['reason']}")
    lines.extend(["", "## Remediation Plan", ""])
    for week in payload["remediationPlanner"]["weeklyPlan"]:
        lines.append(f"### Week {week['week']}: {week['focus']}")
        for action in week["actions"]:
            lines.append(f"- `{action['playbook']}` ({action['findingCount']} findings): {action['firstAction']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI/KI advisory insights from AXPA evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown-output", default="")
    parser.add_argument("--question", default="")
    args = parser.parse_args()

    payload = generate_ai_insights(args.evidence, args.question)
    write_json(args.output, payload)
    if args.markdown_output:
        Path(args.markdown_output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown_output).write_text(render_markdown(payload), encoding="utf-8")
        print(f"Wrote {args.markdown_output}")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
