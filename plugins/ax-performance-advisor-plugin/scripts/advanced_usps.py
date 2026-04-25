from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _load_known_issues() -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / "rules" / "known_issues.json"
    return json.loads(path.read_text(encoding="utf-8")).get("patterns", [])


def _top(findings: list[dict[str, Any]], n: int = 12) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: RANK.get(f.get("severity"), 0), reverse=True)[:n]


def slo_burn_rate(findings: list[dict[str, Any]]) -> dict[str, Any]:
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    items = []
    for playbook, count in playbooks.most_common():
        high = sum(1 for f in findings if f.get("recommendation", {}).get("playbook") == playbook and f.get("severity") in {"critical", "high"})
        budget = 2
        burn = round(high / budget, 2)
        items.append({"slo": f"{playbook}-weekly-high-risk-budget", "budget": budget, "currentHighRisk": high, "burnRate": burn, "status": "breached" if burn > 1 else "watch" if burn else "ok"})
    return {"sloCount": len(items), "items": items}


def maintenance_window_optimizer(findings: list[dict[str, Any]]) -> dict[str, Any]:
    groups = defaultdict(list)
    for finding in findings:
        playbook = finding.get("recommendation", {}).get("playbook", "review")
        groups[playbook].append(finding)
    sequence = []
    order = ["collector-fix", "stale-statistics", "sql-wait-analysis", "missing-composite-index-candidate", "deployment-regression", "blocking-chain", "parameter-sensitive-plan"]
    for slot, playbook in enumerate(order, start=1):
        if playbook in groups:
            sequence.append({"slot": slot, "window": f"T+{(slot-1)*30:02d}m", "playbook": playbook, "findingCount": len(groups[playbook]), "proposal": "Run in controlled TEST/maintenance window; collect post-window evidence."})
    return {"sequenceCount": len(sequence), "sequence": sequence}


def cost_of_delay(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for f in _top(findings, 30):
        score = RANK.get(f.get("severity"), 1) * (2 if f.get("performanceDebt", {}).get("isDebt") else 1)
        rows.append({"findingId": f["id"], "title": f["title"], "dailyRiskPoints": score, "reason": f"{f.get('severity')} severity; debt={f.get('performanceDebt', {}).get('isDebt')}"})
    return {"totalDailyRiskPoints": sum(r["dailyRiskPoints"] for r in rows), "items": rows}


def release_gate(findings: list[dict[str, Any]]) -> dict[str, Any]:
    blockers = [f for f in findings if f.get("severity") in {"critical", "high"}]
    return {"status": "block" if blockers else "pass", "blockerCount": len(blockers), "blockers": [{"findingId": f["id"], "title": f["title"], "severity": f["severity"]} for f in blockers[:20]]}


def retention_candidates(findings: list[dict[str, Any]]) -> dict[str, Any]:
    tables = Counter()
    for f in findings:
        if f.get("dataGrowth", {}).get("isGrowthDriven") or f.get("recommendation", {}).get("playbook") in {"stale-statistics", "data-growth"}:
            for table in f.get("axContext", {}).get("tables", []):
                tables[table] += 1
    return {"candidateCount": len(tables), "candidates": [{"table": t, "signals": c, "proposal": "Review retention/archive policy with business owner before tuning further."} for t, c in tables.most_common(30)]}


def known_issue_matches(findings: list[dict[str, Any]]) -> dict[str, Any]:
    patterns = _load_known_issues()
    matches = []
    for f in findings:
        playbook = f.get("recommendation", {}).get("playbook", "")
        for p in patterns:
            if p["matchPlaybook"] == playbook:
                matches.append({"findingId": f["id"], "knownIssueId": p["id"], "title": p["title"], "fixPath": p["fixPath"], "validation": p["validation"]})
    return {"matchCount": len(matches), "matches": matches[:100]}


def executive_briefings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    sev = Counter(f.get("severity") for f in findings)
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    brief = {
        "oneMinute": f"{len(findings)} findings; {sev['high'] + sev['critical']} high/critical. Dominant themes: {', '.join(k for k, _ in playbooks.most_common(3))}.",
        "decisionAsk": "Approve TEST validation for high-risk findings and schedule low-risk maintenance items.",
        "riskIfDeferred": "Recurring debt increases batch/runtime risk and weakens SQL Server 2016 support-exit readiness.",
    }
    return brief


def generate_advanced_usps(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "sloBurnRate": slo_burn_rate(findings),
        "maintenanceWindowOptimizer": maintenance_window_optimizer(findings),
        "costOfDelay": cost_of_delay(findings),
        "releaseGate": release_gate(findings),
        "retentionCandidates": retention_candidates(findings),
        "knownIssueMatches": known_issue_matches(findings),
        "executiveBriefings": executive_briefings(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate additional AXPA USP feature pack.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_advanced_usps(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote advanced USP pack to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
