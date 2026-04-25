from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import SEVERITY_RANK, analyze_evidence, load_evidence, write_json


READ_ONLY_COMMANDS = {
    "sql_snapshot": ".\\scripts\\collect_sql_snapshot.ps1 -ConnectionString \"Server={server};Database={database};Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True\" -OutputDirectory .\\evidence\\{environment} -AxDatabaseName {database} -IncludeQueryStore -IncludeDeadlocks -WaitDeltaSeconds 60",
    "ax_db_snapshot": ".\\scripts\\collect_ax_db_snapshot.ps1 -ConnectionString \"Server={server};Database={database};Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True\" -OutputDirectory .\\evidence\\{environment} -Days 14",
    "aos_counters": ".\\scripts\\collect_aos_counters.ps1 -ComputerName {server} -OutputDirectory .\\evidence\\{environment} -SampleSeconds 30",
}


def _ranked(findings: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_RANK.get(f.get("severity", "informational"), 0),
            len(f.get("evidence", [])),
            1 if f.get("confidence") == "high" else 0,
        ),
        reverse=True,
    )[:limit]


def _target_defaults(evidence: str | Path) -> dict[str, str]:
    loaded = load_evidence(evidence)
    root_name = Path(evidence).name or "environment"
    metadata = loaded.metadata
    config = loaded.config
    return {
        "environment": str(config.get("environment") or metadata.get("environment") or root_name),
        "server": str(config.get("server") or metadata.get("server") or root_name),
        "database": str(config.get("database") or metadata.get("database") or "AXDB"),
    }


def investigation_queue(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for finding in _ranked(findings, 12):
        playbook = finding.get("recommendation", {}).get("playbook", "review")
        evidence_sources = [e.get("source", "") for e in finding.get("evidence", [])]
        needs_trace = not finding.get("axContext", {}).get("classes")
        next_evidence = []
        if "sql_wait_stats" not in evidence_sources:
            next_evidence.append("wait delta snapshot")
        if "sql_top_queries" not in evidence_sources and playbook in {"missing-composite-index-candidate", "parameter-sensitive-plan"}:
            next_evidence.append("top query and plan evidence")
        if needs_trace:
            next_evidence.append("Trace Parser or DynamicsPerf X++ evidence")
        if not next_evidence:
            next_evidence.append("post-change validation evidence")
        rows.append({
            "findingId": finding["id"],
            "title": finding["title"],
            "priority": finding.get("severity", "medium"),
            "owner": finding.get("recommendation", {}).get("owner") or finding.get("axContext", {}).get("technicalOwner", "AX Operations"),
            "hypothesis": finding.get("likelyCause", "Root cause requires evidence correlation."),
            "nextQuestion": f"Can {playbook} be proven for {finding['id']} with current evidence?",
            "nextEvidence": next_evidence,
            "stopRule": "Stop before any productive change if evidence is missing, risk is high, or approval is absent.",
            "decision": "ready-for-review" if len(finding.get("evidence", [])) >= 1 else "needs-evidence",
        })
    return rows


def follow_up_questions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for finding in _ranked(findings, 20):
        readiness = finding.get("changeReadiness", {})
        questions = [
            {
                "question": "Soll ich die fehlende Evidence als Collector-Auftrag vorbereiten?",
                "effect": "Erzeugt read-only Sammelkommandos und markiert benoetigte Rechte.",
                "actionType": "evidence-plan",
            },
            {
                "question": "Soll ich daraus ein CAB-/GxP-Change-Paket vorbereiten?",
                "effect": "Erzeugt Beschreibung, Risiko, Testplan, Rollback und Approval-Pfad.",
                "actionType": "change-draft",
            },
            {
                "question": "Soll ich den TEST-Validierungsplan erzeugen?",
                "effect": "Erzeugt Baseline-, Test- und Post-Change-Messpunkte.",
                "actionType": "validation-plan",
            },
        ]
        if readiness.get("technicalRisk") in {"high", "medium-high"}:
            questions.append({
                "question": "Soll ich zuerst eine Risiko-/Blast-Radius-Pruefung planen?",
                "effect": "Priorisiert betroffene Module, Tabellen, Owner und Rollback-Komplexitaet.",
                "actionType": "blast-radius",
            })
        rows.append({"findingId": finding["id"], "title": finding["title"], "questions": questions})
    return rows


def evidence_acquisition_planner(evidence: str | Path) -> dict[str, Any]:
    loaded = load_evidence(evidence)
    defaults = _target_defaults(evidence)
    checks = [
        ("sql_top_queries", "SQL DMV top query snapshot", READ_ONLY_COMMANDS["sql_snapshot"]),
        ("sql_wait_stats", "SQL wait stats snapshot", READ_ONLY_COMMANDS["sql_snapshot"]),
        ("blocking", "SQL blocking snapshot", READ_ONLY_COMMANDS["sql_snapshot"]),
        ("batch_jobs", "AX batch history snapshot", READ_ONLY_COMMANDS["ax_db_snapshot"]),
        ("user_sessions", "AX user sessions snapshot", READ_ONLY_COMMANDS["ax_db_snapshot"]),
        ("aos_counters", "AOS and Windows performance counters", READ_ONLY_COMMANDS["aos_counters"]),
        ("trace_parser", "Trace Parser import for X++ call stacks", "python .\\scripts\\import_trace_parser_export.py --input <trace-export.csv> --output .\\evidence\\{environment}\\trace_parser.csv"),
        ("dynamicsperf", "DynamicsPerf import for historical AX/SQL correlation", "python .\\scripts\\import_dynamicsperf_export.py --input <dynamicsperf-export.csv> --output .\\evidence\\{environment}\\dynamicsperf.csv"),
    ]
    tasks = []
    for table, label, command in checks:
        present = bool(loaded.tables.get(table))
        tasks.append({
            "source": table,
            "label": label,
            "status": "present" if present else "missing",
            "mode": "read-only" if table not in {"trace_parser", "dynamicsperf"} else "import",
            "command": command.format(**defaults),
            "requires": "SQL read/VIEW SERVER STATE" if table.startswith("sql_") or table == "blocking" else "AX DB read or exported file",
        })
    return {"target": defaults, "tasks": tasks, "missingCount": sum(1 for t in tasks if t["status"] == "missing")}


def change_drafts(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for finding in _ranked(findings, 12):
        readiness = finding.get("changeReadiness", {})
        validation = finding.get("validation", {})
        rows.append({
            "findingId": finding["id"],
            "title": finding["title"],
            "changeType": "Standard validation" if finding.get("severity") in {"low", "medium"} else "Normal CAB change",
            "approvalPath": readiness.get("approvalPath", "CAB"),
            "risk": {
                "technical": readiness.get("technicalRisk", "medium"),
                "axCompatibility": readiness.get("axCompatibilityRisk", "medium"),
                "downtime": readiness.get("downtimeRisk", "low"),
                "rollback": readiness.get("rollbackComplexity", "medium"),
            },
            "testPlan": [
                "Sichere Baseline aus aktueller AXPA Evidence archivieren.",
                f"Erfolgskriterium pruefen: {validation.get('successMetric', 'before/after evidence improves')}",
                "Aenderung nur in TEST oder Wartungsfenster validieren.",
                "Post-Change Evidence mit identischem Collector-Set erfassen.",
            ],
            "rollback": validation.get("rollback", "Approved change through change control rollback path revertieren."),
        })
    return rows


def validation_run_planner(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for finding in _ranked(findings, 12):
        val = finding.get("validation", {})
        rows.append({
            "findingId": finding["id"],
            "baselineWindow": val.get("baselineWindow", "current evidence window"),
            "postChangeWindow": val.get("postChangeWindow", "one comparable business cycle"),
            "successMetric": val.get("successMetric", "risk metric improves without regression"),
            "requiredFiles": ["metadata.json", "sql_top_queries.csv", "sql_wait_stats.csv"],
            "comparisonCommand": "python .\\scripts\\compare_baseline.py --before .\\evidence\\before --after .\\evidence\\after --output .\\out\\validation-comparison.json",
        })
    return rows


def readiness_gate(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for finding in _ranked(findings, 25):
        checks = {
            "evidence": bool(finding.get("evidence")),
            "owner": bool(finding.get("recommendation", {}).get("owner")),
            "approval": bool(finding.get("changeReadiness", {}).get("approvalPath")),
            "rollback": bool(finding.get("validation", {}).get("rollback")),
            "successMetric": bool(finding.get("validation", {}).get("successMetric")),
        }
        passed = sum(1 for value in checks.values() if value)
        if passed == len(checks) and finding.get("severity") not in {"critical", "high"}:
            status = "ready-for-test"
        elif passed >= 4:
            status = "requires-approval"
        else:
            status = "needs-more-evidence"
        rows.append({"findingId": finding["id"], "title": finding["title"], "status": status, "score": passed, "checks": checks})
    return rows


def operator_decision_memory(findings: list[dict[str, Any]]) -> dict[str, Any]:
    groups = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    return {
        "status": "prepared",
        "memoryModel": "local-json/sqlite-ready",
        "suggestedFeedbackFields": ["findingId", "decision", "reason", "owner", "validatedEffect", "capturedAt"],
        "playbookBacklog": [{"playbook": name, "openFindings": count, "defaultDecision": "review"} for name, count in groups.most_common()],
    }


def next_best_actions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = []
    for finding in _ranked(findings, 10):
        status = "Collect evidence"
        if finding.get("evidence"):
            status = "Prepare validation"
        if finding.get("severity") in {"critical", "high"} and finding.get("evidence"):
            status = "Prepare CAB package"
        actions.append({
            "findingId": finding["id"],
            "action": status,
            "whyThisFirst": f"{finding.get('severity')} severity, {finding.get('confidence')} confidence, {len(finding.get('evidence', []))} evidence points.",
            "safeBoundary": "No production change from this panel; produce evidence, scripts, or change drafts only.",
        })
    return actions


def executive_risk_briefing(findings: list[dict[str, Any]]) -> dict[str, Any]:
    severity = Counter(f.get("severity") for f in findings)
    modules = Counter(f.get("axContext", {}).get("module", "Unknown") for f in findings)
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    return {
        "headline": f"{len(findings)} AX/SQL performance findings; {severity['critical'] + severity['high']} high-priority items need controlled validation.",
        "topBusinessAreas": [name for name, _ in modules.most_common(5)],
        "topRiskThemes": [name for name, _ in playbooks.most_common(5)],
        "decisionAsk": "Approve read-only evidence completion and TEST validation for the highest-risk root-cause groups.",
        "nonGoal": "No automatic production tuning or index creation without explicit admin approval.",
    }


def generate_autonomous_ops(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "featureCount": 20,
        "investigationQueue": investigation_queue(findings),
        "followUpQuestions": follow_up_questions(findings),
        "evidenceAcquisitionPlanner": evidence_acquisition_planner(evidence),
        "changeDrafts": change_drafts(findings),
        "validationRunPlanner": validation_run_planner(findings),
        "readinessGate": readiness_gate(findings),
        "operatorDecisionMemory": operator_decision_memory(findings),
        "nextBestActions": next_best_actions(findings),
        "executiveRiskBriefing": executive_risk_briefing(findings),
        "safeToAutomateClassifier": [
            {"findingId": item["findingId"], "classification": "safe-to-plan" if item["status"] == "ready-for-test" else "human-approval-required", "reason": item["status"]}
            for item in readiness_gate(findings)
        ],
        "postChangeEvidenceChecklist": ["sql_top_queries.csv", "sql_wait_stats.csv", "blocking.csv", "metadata.json", "validation-comparison.json"],
        "falsePositiveSuppression": [{"playbook": name, "rule": "Suppress only with owner, expiry, and evidence note.", "candidateCount": count} for name, count in Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings).most_common()],
        "businessImpactReframing": [{"findingId": f["id"], "message": f"{f.get('axContext', {}).get('module', 'Unknown')} risk: {f.get('businessImpact', {}).get('impact', f['title'])}"} for f in _ranked(findings, 15)],
        "adminApprovalReadinessGate": [{"findingId": r["findingId"], "readyForAdminQuestion": r["status"] in {"ready-for-test", "requires-approval"}, "status": r["status"]} for r in readiness_gate(findings)],
        "rootCauseDecisionTree": [{"findingId": q["findingId"], "question": q["nextQuestion"], "yes": "prepare validation/change draft", "no": "collect nextEvidence", "nextEvidence": q["nextEvidence"]} for q in investigation_queue(findings)],
        "hypothesisConfidenceTimeline": [{"findingId": f["id"], "current": f.get("confidence", "unknown"), "nextMilestone": "high after direct time-window correlation and post-change evidence"} for f in _ranked(findings, 15)],
        "findingToQuestionCopilot": [{"findingId": item["findingId"], "questions": [q["question"] for q in item["questions"]]} for item in follow_up_questions(findings)],
        "rollbackReadinessScore": [{"findingId": r["findingId"], "score": r["score"], "status": "ready" if r["checks"].get("rollback") else "missing-rollback"} for r in readiness_gate(findings)],
        "recommendationAcceptanceLearning": {"status": "ready-for-feedback", "fields": ["accepted", "rejected", "validated", "deferred"], "memory": operator_decision_memory(findings)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate autonomous AXPA operations artifacts.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_autonomous_ops(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote autonomous ops pack to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
