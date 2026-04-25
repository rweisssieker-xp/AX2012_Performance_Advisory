from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def what_if_simulation(findings: list[dict[str, Any]]) -> dict[str, Any]:
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    scenarios = []
    for playbook, count in playbooks.most_common(8):
        affected = [f for f in findings if f.get("recommendation", {}).get("playbook") == playbook]
        current = sum(RANK.get(f.get("severity"), 1) for f in affected)
        scenarios.append(
            {
                "scenario": f"Resolve top {playbook} findings",
                "playbook": playbook,
                "affectedFindings": count,
                "currentRiskPoints": current,
                "estimatedResidualRiskPoints": round(current * 0.35),
                "riskReductionPercent": 65,
                "requiresValidation": True,
            }
        )
    return {"scenarioCount": len(scenarios), "scenarios": scenarios}


def baseline_benchmark(findings: list[dict[str, Any]]) -> dict[str, Any]:
    severity = Counter(f.get("severity", "unknown") for f in findings)
    score = max(0, 100 - sum(RANK.get(f.get("severity"), 1) for f in findings))
    return {
        "baselineName": "current-run",
        "healthScore": score,
        "severityMix": dict(severity),
        "benchmarkInterpretation": "Use this as local baseline until at least 7 comparable evidence runs exist.",
    }


def evidence_completeness_roadmap(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    files = {p.name.lower() for p in root.glob("*")}
    desired = [
        ("trace_parser.csv", "X++ attribution"),
        ("dynamicsperf_trace.csv", "DynamicsPerf call-stack attribution"),
        ("deadlocks.csv", "deadlock root cause"),
        ("batch_jobs.csv", "batch collision proof"),
        ("user_sessions.csv", "user impact mapping"),
        ("query_store_runtime.csv", "runtime regression proof"),
        ("sql_top_queries.csv", "query ranking"),
        ("sql_wait_stats.csv", "wait correlation"),
    ]
    rows = []
    for file_name, value in desired:
        present = file_name in files and (root / file_name).stat().st_size > 0
        rows.append({"source": file_name, "present": present, "value": value, "priority": "high" if not present else "done"})
    return {"complete": all(r["present"] for r in rows), "sources": rows}


def remediation_kanban(findings: list[dict[str, Any]]) -> dict[str, Any]:
    lanes = {"Now": [], "Next": [], "Later": [], "Waiting Evidence": []}
    for f in findings:
        sev = f.get("severity")
        confidence = f.get("confidence")
        item = {"findingId": f["id"], "title": f["title"], "severity": sev, "playbook": f.get("recommendation", {}).get("playbook", "review")}
        if confidence == "low":
            lanes["Waiting Evidence"].append(item)
        elif sev in {"critical", "high"}:
            lanes["Now"].append(item)
        elif sev == "medium":
            lanes["Next"].append(item)
        else:
            lanes["Later"].append(item)
    return {lane: items[:30] for lane, items in lanes.items()}


def kpi_contracts(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    return [
        {
            "kpi": f"{playbook}.open_findings",
            "target": "<= 2 high findings per comparable run",
            "current": count,
            "owner": "AX Operations",
            "reviewCadence": "weekly",
        }
        for playbook, count in playbooks.most_common(12)
    ]


def capability_matrix() -> list[dict[str, Any]]:
    return [
        {"capability": "AX-aware SQL diagnostics", "status": "implemented", "differentiator": "AX table/module/playbook context"},
        {"capability": "Enterprise observability", "status": "implemented", "differentiator": "time-series, alerts, estate, plan repository"},
        {"capability": "Admin execution", "status": "guarded-preview", "differentiator": "tokens, gates, no blind PROD execution"},
        {"capability": "External push", "status": "requires-config", "differentiator": "payloads generated without credential leakage"},
        {"capability": "X++ attribution", "status": "evidence-gated", "differentiator": "Trace Parser/DynamicsPerf when available"},
        {"capability": "Local RAG/Q&A", "status": "implemented", "differentiator": "source finding IDs, no external LLM required"},
    ]


def generate_strategy_extensions(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "whatIfSimulation": what_if_simulation(findings),
        "baselineBenchmark": baseline_benchmark(findings),
        "evidenceCompletenessRoadmap": evidence_completeness_roadmap(evidence),
        "remediationKanban": remediation_kanban(findings),
        "kpiContracts": kpi_contracts(findings),
        "capabilityMatrix": capability_matrix(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA strategy extension pack.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_strategy_extensions(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote strategy extensions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
