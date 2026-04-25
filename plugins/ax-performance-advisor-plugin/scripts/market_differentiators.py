from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, module_health_scores, write_json


def vendor_neutral_comparison() -> dict[str, Any]:
    return {
        "genericToolsStrength": ["continuous monitoring", "large-scale alerting", "APM integrations", "SaaS operations"],
        "axpaStrength": ["AX 2012 table/process context", "GxP/ITIL recommendation evidence", "admin execution gates", "AX batch/business correlation"],
        "positioning": "Use AXPA as AX-specific interpretation and governance layer alongside or instead of generic database monitoring.",
    }


def migration_readiness(findings: list[dict[str, Any]]) -> dict[str, Any]:
    signals = []
    for f in findings:
        playbook = f.get("recommendation", {}).get("playbook", "")
        if playbook in {"data-growth", "deployment-regression", "parameter-sensitive-plan"} or f.get("performanceDebt", {}).get("isDebt"):
            signals.append({"findingId": f["id"], "theme": playbook or "performance-debt", "reason": f.get("likelyCause", "")})
    score = max(0, 100 - min(100, len(signals) * 3))
    return {"readinessScore": score, "signalCount": len(signals), "signals": signals[:50], "recommendation": "Use these signals for D365/data-platform modernization scoping."}


def resilience_score(findings: list[dict[str, Any]]) -> dict[str, Any]:
    high = sum(1 for f in findings if f.get("severity") in {"critical", "high"})
    debt = sum(1 for f in findings if f.get("performanceDebt", {}).get("isDebt"))
    approvals = sum(1 for f in findings if f.get("recommendation", {}).get("requiresApproval"))
    score = max(0, 100 - high * 6 - debt * 2 - approvals // 10)
    return {"score": score, "highFindings": high, "debtItems": debt, "approvalItems": approvals, "interpretation": "Higher score means fewer urgent risks, less debt, and easier controlled change."}


def knowledge_graph(findings: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = {}
    edges = []
    def node(node_id: str, kind: str, label: str):
        nodes[node_id] = {"id": node_id, "kind": kind, "label": label}
    for f in findings:
        fid = f"finding:{f['id']}"
        node(fid, "finding", f["title"])
        playbook = f.get("recommendation", {}).get("playbook", "review")
        pid = f"playbook:{playbook}"
        node(pid, "playbook", playbook)
        edges.append({"from": fid, "to": pid, "type": "uses-playbook"})
        module = f.get("axContext", {}).get("module", "Unknown")
        mid = f"module:{module}"
        node(mid, "module", module)
        edges.append({"from": fid, "to": mid, "type": "affects-module"})
        for table in f.get("axContext", {}).get("tables", [])[:5]:
            tid = f"table:{table}"
            node(tid, "table", table)
            edges.append({"from": fid, "to": tid, "type": "affects-table"})
    return {"nodeCount": len(nodes), "edgeCount": len(edges), "nodes": list(nodes.values())[:500], "edges": edges[:1000]}


def process_owner_scorecards(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = defaultdict(list)
    for f in findings:
        owner = f.get("axContext", {}).get("businessOwner", "Unknown")
        groups[owner].append(f)
    rows = []
    for owner, items in groups.items():
        high = sum(1 for f in items if f.get("severity") in {"critical", "high"})
        rows.append({"owner": owner, "findingCount": len(items), "highCount": high, "topModules": [m for m, _ in Counter(f.get("axContext", {}).get("module", "Unknown") for f in items).most_common(3)], "score": max(0, 100 - high * 10 - len(items))})
    return sorted(rows, key=lambda r: r["score"])


def evidence_marketplace(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    needed = {
        "trace_parser.csv": "Unlock X++ class/method attribution",
        "dynamicsperf_trace.csv": "Unlock historical AX/SQL call-stack correlation",
        "deadlocks.csv": "Unlock deadlock graph root cause",
        "batch_jobs.csv": "Unlock batch schedule optimizer proof",
        "user_sessions.csv": "Unlock user impact and role correlation",
    }
    return [{"evidence": k, "value": v, "requestText": f"Please provide {k} for the same time window as the current AXPA run."} for k, v in needed.items()]


def value_realization(findings: list[dict[str, Any]]) -> dict[str, Any]:
    by_playbook = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    opportunities = []
    for playbook, count in by_playbook.most_common():
        opportunities.append({"initiative": playbook, "findingCount": count, "expectedValue": "reduced risk and faster comparable business window", "proof": "requires before/after AXPA run"})
    return {"opportunityCount": len(opportunities), "opportunities": opportunities}


def generate_market_differentiators(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "vendorNeutralComparison": vendor_neutral_comparison(),
        "migrationReadiness": migration_readiness(findings),
        "resilienceScore": resilience_score(findings),
        "knowledgeGraph": knowledge_graph(findings),
        "processOwnerScorecards": process_owner_scorecards(findings),
        "evidenceMarketplace": evidence_marketplace(findings),
        "valueRealization": value_realization(findings),
        "moduleScores": module_health_scores(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA market differentiator USP pack.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_market_differentiators(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote market differentiators to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
