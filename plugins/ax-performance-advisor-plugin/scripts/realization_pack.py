from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


def _collector_errors(evidence: str | Path) -> list[dict[str, Any]]:
    root = Path(evidence)
    rows = []
    for path in sorted(root.glob("*.error.csv")):
        message = path.read_text(encoding="utf-8", errors="replace").strip()
        lower = message.lower()
        if "timeout" in lower:
            cause = "timeout"
            fix = "Reduce collector scope/top-N, increase command timeout, or schedule this collector outside peak workload."
        elif "invalid column" in lower or "column" in lower:
            cause = "schema-drift"
            fix = "Run schema discovery and adapt the collector column projection for this AX localization/customization."
        elif "permission" in lower or "denied" in lower or "login" in lower:
            cause = "permission"
            fix = "Grant read-only DMV/table access required by the collector; do not grant write permissions."
        else:
            cause = "collector-error"
            fix = "Inspect the error text and add a bounded read-only fallback query."
        rows.append({"source": path.name, "cause": cause, "fixProposal": fix, "message": message[:800]})
    return rows


def _evidence_files(evidence: str | Path) -> set[str]:
    root = Path(evidence)
    return {p.name.lower() for p in root.glob("*")} if root.exists() else set()


def _trust_score(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    files = _evidence_files(evidence)
    expected = ["sql_top_queries", "sql_wait_stats", "statistics_age", "file_latency", "tempdb", "query_store", "blocking", "deadlock", "batch", "aos"]
    present = [name for name in expected if any(name in file for file in files)]
    errors = _collector_errors(evidence)
    direct = sum(1 for f in findings if f.get("evidence"))
    completeness = round(len(present) / len(expected) * 100)
    collector_health = max(0, 100 - len(errors) * 12)
    evidence_density = round(direct / max(1, len(findings)) * 100)
    score = round(completeness * 0.45 + collector_health * 0.35 + evidence_density * 0.20)
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
    return {
        "score": score,
        "grade": grade,
        "completeness": completeness,
        "collectorHealth": collector_health,
        "evidenceDensity": evidence_density,
        "presentSources": present,
        "missingSources": [name for name in expected if name not in present],
        "collectorErrors": len(errors),
    }


def _role_briefings(findings: list[dict[str, Any]]) -> dict[str, list[str]]:
    top = sorted(findings, key=lambda f: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(f.get("severity"), 0), reverse=True)[:8]
    return {
        "DBA": [f"{f['id']}: {f['title']} - {f.get('recommendation', {}).get('playbook', 'review')}" for f in top if f.get("sqlContext")],
        "AX Developer": [f"{f['id']}: review AX table/class context {', '.join(f.get('axContext', {}).get('tables', [])[:3]) or 'requires Trace Parser'}" for f in top],
        "Operations": [f"{f['id']}: {f.get('recommendation', {}).get('summary', '')}" for f in top],
        "QA/GxP": [f"{f['id']}: validate with {f.get('validation', {}).get('successMetric', 'before/after evidence')}" for f in top],
        "CIO": [f"{f.get('severity', '').upper()}: {f['title']} ({f.get('axContext', {}).get('module', 'Unknown')})" for f in top[:5]],
    }


def _sla_contracts(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    contracts = []
    for playbook, count in playbooks.most_common(8):
        contracts.append(
            {
                "name": f"AXPA-{playbook}-contract",
                "scope": playbook,
                "candidateSlo": "No recurring high-severity finding for this playbook in a comparable business window.",
                "errorBudget": "0 critical, <=2 high findings per weekly review window.",
                "approvalStatus": "candidate",
                "evidenceBasis": f"{count} current findings",
            }
        )
    return contracts


def _synthetic_replay(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps = []
    for finding in findings[:12]:
        steps.append(
            {
                "findingId": finding.get("id"),
                "workload": finding.get("recommendation", {}).get("playbook", "review"),
                "testDataNeed": "Use restored TEST data with comparable table cardinality and company distribution.",
                "replayAction": f"Replay representative workload for {finding.get('axContext', {}).get('module', 'Unknown')} and collect SQL waits, Query Store runtime, and AX batch/session evidence.",
                "passCriteria": finding.get("validation", {}).get("successMetric", "No regression against baseline."),
            }
        )
    return steps


def _governance_state(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "findingId": f.get("id"),
            "state": f.get("status", "proposed"),
            "nextState": "approved" if f.get("severity") in {"critical", "high"} else "scheduled",
            "requiredEvidence": ["approval", "test-result", "rollback-note", "post-change-evidence"],
            "owner": f.get("axContext", {}).get("technicalOwner", "AX Operations"),
        }
        for f in findings[:30]
    ]


def _adapter_readiness() -> dict[str, Any]:
    return {
        "powerBiPush": {"status": "requires-config", "required": ["workspaceId", "datasetId", "credential"]},
        "azureDevOpsPush": {"status": "requires-config", "required": ["organizationUrl", "project", "PAT or managed identity"]},
        "jiraPush": {"status": "requires-config", "required": ["baseUrl", "projectKey", "credential"]},
        "llmChat": {"status": "requires-config", "required": ["model provider", "API key or local endpoint", "evidence index path"]},
    }


def _sql2016_risk(findings: list[dict[str, Any]]) -> dict[str, Any]:
    high = sum(1 for f in findings if f.get("severity") in {"critical", "high"})
    debt = sum(1 for f in findings if f.get("performanceDebt", {}).get("isDebt"))
    risk = "high" if high >= 5 or debt >= 10 else "medium" if high or debt else "low"
    return {
        "platform": "SQL Server 2016",
        "supportRiskDate": "2026-07-14",
        "risk": risk,
        "drivers": {"highFindings": high, "performanceDebtItems": debt},
        "recommendation": "Use current AXPA findings as input for SQL Server upgrade, ESU, or D365 modernization planning.",
    }


def generate_realization_pack(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "evidenceTrustScore": _trust_score(evidence, findings),
        "collectorFixSuggestions": _collector_errors(evidence),
        "roleBasedBriefings": _role_briefings(findings),
        "dynamicSlaContracts": _sla_contracts(findings),
        "syntheticLoadReplayPlan": _synthetic_replay(findings),
        "closedLoopGovernance": _governance_state(findings),
        "adapterReadiness": _adapter_readiness(),
        "sql2016EndOfSupportRisk": _sql2016_risk(findings),
        "axCodeRemediationDiffAssistant": {
            "status": "evidence-gated",
            "requiredEvidence": "Trace Parser/DynamicsPerf call stack plus X++ source path.",
            "realBehavior": "Produces no fake diff until the required source evidence exists.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the real-feature closure pack for prepared AXPA capabilities.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_realization_pack(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
