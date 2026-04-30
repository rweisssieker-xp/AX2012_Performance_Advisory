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


def performance_digital_twin(findings: list[dict[str, Any]]) -> dict[str, Any]:
    modules = Counter(f.get("axContext", {}).get("module", "Unknown") for f in findings)
    tables = Counter(table for f in findings for table in f.get("axContext", {}).get("tables", []))
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    return {
        "nodeCount": len(modules) + len(tables) + len(playbooks),
        "layers": {
            "businessProcesses": [{"name": k, "riskSignals": v} for k, v in modules.most_common(20)],
            "hotTables": [{"name": k, "riskSignals": v} for k, v in tables.most_common(30)],
            "rootCauseFamilies": [{"name": k, "riskSignals": v} for k, v in playbooks.most_common(20)],
        },
        "use": "Exportable AX performance twin for topology, process, table, and root-cause reasoning.",
    }


def causal_graph_engine(findings: list[dict[str, Any]]) -> dict[str, Any]:
    edges = []
    for f in findings[:250]:
        playbook = f.get("recommendation", {}).get("playbook", "review")
        for table in f.get("axContext", {}).get("tables", [])[:4]:
            edges.append({"from": table, "to": playbook, "type": "contributes-to", "findingId": f["id"]})
        for wait in f.get("sqlContext", {}).get("waitTypes", [])[:4]:
            edges.append({"from": wait, "to": playbook, "type": "supports-cause", "findingId": f["id"]})
        module = f.get("axContext", {}).get("module", "Unknown")
        edges.append({"from": playbook, "to": module, "type": "impacts", "findingId": f["id"]})
    nodes = {edge["from"] for edge in edges} | {edge["to"] for edge in edges}
    return {"nodeCount": len(nodes), "edgeCount": len(edges), "edges": edges[:1000]}


def performance_contract_tests(findings: list[dict[str, Any]]) -> dict[str, Any]:
    contracts = []
    for f in findings[:100]:
        metric = (f.get("evidence") or [{}])[0].get("metric", "risk_score")
        value = (f.get("evidence") or [{}])[0].get("value", "")
        threshold = (f.get("evidence") or [{}])[0].get("threshold", "")
        contracts.append({
            "findingId": f["id"],
            "contract": f"{metric} must improve after remediation",
            "currentValue": value,
            "target": threshold or "below current baseline",
            "testCommand": f"python scripts/run_axpa_pipeline.py --environment validation --server SERVER --database AXDB --evidence evidence/validation --out out",
        })
    return {"contractCount": len(contracts), "contracts": contracts}


def change_blast_radius(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for playbook, count in Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings).most_common():
        affected_modules = sorted({f.get("axContext", {}).get("module", "Unknown") for f in findings if f.get("recommendation", {}).get("playbook", "review") == playbook})
        affected_tables = sorted({table for f in findings if f.get("recommendation", {}).get("playbook", "review") == playbook for table in f.get("axContext", {}).get("tables", [])})
        rows.append({"changeType": playbook, "findingCount": count, "modules": affected_modules[:8], "tables": affected_tables[:12], "blastRadius": "high" if len(affected_modules) > 3 or len(affected_tables) > 10 else "medium" if count > 5 else "low"})
    return {"changeTypes": rows}


def performance_debt_interest(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    rank = {"critical": 10, "high": 7, "medium": 4, "low": 1}
    for f in findings:
        recurrence = int(f.get("performanceDebt", {}).get("recurrenceCount") or 1)
        age = int(f.get("performanceDebt", {}).get("ageDays") or 0)
        interest = rank.get(f.get("severity"), 1) * recurrence + age // 7
        if f.get("performanceDebt", {}).get("isDebt") or interest >= 8:
            rows.append({"findingId": f["id"], "title": f["title"], "interest": interest, "recurrence": recurrence, "ageDays": age, "owner": f.get("recommendation", {}).get("owner", "")})
    return {"debtItemCount": len(rows), "items": sorted(rows, key=lambda x: x["interest"], reverse=True)[:100]}


def remediation_portfolio_optimizer(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    benefit_map = {"high": 5, "medium": 3, "low": 1}
    risk_map = {"high": 5, "medium": 3, "low": 1}
    for f in findings:
        benefit = benefit_map.get(f.get("changeReadiness", {}).get("benefit", "medium"), 3)
        risk = risk_map.get(f.get("changeReadiness", {}).get("technicalRisk", "medium"), 3)
        confidence = 2 if f.get("confidence") == "high" else 1
        score = round((benefit * confidence) / max(1, risk), 2)
        rows.append({"findingId": f["id"], "title": f["title"], "score": score, "benefit": benefit, "risk": risk, "firstMove": f.get("recommendation", {}).get("summary", "")})
    return {"portfolio": sorted(rows, key=lambda x: x["score"], reverse=True)[:50]}


def ax_aging_risk_index(findings: list[dict[str, Any]]) -> dict[str, Any]:
    high = sum(1 for f in findings if f.get("severity") in {"critical", "high"})
    growth = sum(1 for f in findings if f.get("dataGrowth", {}).get("isGrowthDriven") or f.get("recommendation", {}).get("playbook") in {"data-growth", "stale-statistics"})
    debt = sum(1 for f in findings if f.get("performanceDebt", {}).get("isDebt"))
    score = min(100, high * 2 + growth + debt * 2)
    return {"score": score, "highFindings": high, "growthSignals": growth, "debtSignals": debt, "interpretation": "Higher score means stronger legacy aging pressure and modernization/archiving relevance."}


def regression_test_skeletons(findings: list[dict[str, Any]]) -> dict[str, Any]:
    tests = []
    for f in findings[:60]:
        tests.append({
            "name": f"test_{f['id'].lower().replace('-', '_')}",
            "findingId": f["id"],
            "assertion": f.get("validation", {}).get("successMetric", "Risk should not regress after change."),
            "evidence": [e.get("source") for e in f.get("evidence", [])[:4]],
        })
    return {"testCount": len(tests), "tests": tests}


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
        "performanceDigitalTwin": performance_digital_twin(findings),
        "causalGraphEngine": causal_graph_engine(findings),
        "performanceContractTests": performance_contract_tests(findings),
        "changeBlastRadius": change_blast_radius(findings),
        "performanceDebtInterest": performance_debt_interest(findings),
        "remediationPortfolioOptimizer": remediation_portfolio_optimizer(findings),
        "axAgingRiskIndex": ax_aging_risk_index(findings),
        "regressionTestSkeletons": regression_test_skeletons(findings),
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
