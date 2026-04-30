from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, read_csv, write_json


RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _evidence_root(evidence: str | Path) -> Path:
    return Path(evidence)


def _hour_bucket(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    if " " in text:
        time_part = text.split(" ", 1)[1]
    elif "T" in text:
        time_part = text.split("T", 1)[1]
    else:
        time_part = text
    hour = time_part[:2]
    return f"{hour}:00" if hour.isdigit() else "unknown"


def _num(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return 0.0
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _family_from_text(text: str) -> str:
    upper = text.upper()
    if any(token in upper for token in ["INVENT", "MRP", "PROD", "WHS", "KANBAN"]):
        return "Inventory/Production"
    if any(token in upper for token in ["LEDGER", "JOURNAL", "VEND", "CUST", "GENERALJOURNAL"]):
        return "Finance"
    if any(token in upper for token in ["SALE", "SALES", "RECHNUNG", "INVOICE"]):
        return "Sales"
    if any(token in upper for token in ["PURCH", "VENDOR"]):
        return "Purchasing"
    if any(token in upper for token in ["AIF", "SERVICE", "IMPORT", "EXPORT", "DMF"]):
        return "Integration"
    if any(token in upper for token in ["REPORT", "PRINT", "DRUCK"]):
        return "Reporting"
    return "General AX"


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


def temporal_hotspot_map(evidence: str | Path) -> dict[str, Any]:
    root = _evidence_root(evidence)
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    for row in read_csv(root / "batch_tasks.csv"):
        buckets[_hour_bucket(row.get("start_time"))]["batchTasks"] += 1
    for row in read_csv(root / "ax_live_blocking.csv"):
        buckets[_hour_bucket(row.get("check_time"))]["liveBlocking"] += 1
    for row in read_csv(root / "query_store_runtime.csv"):
        hour = _hour_bucket(row.get("start_time"))
        if _num(row.get("avg_duration_ms")) > 1000 or _num(row.get("avg_logical_io_reads")) > 100000:
            buckets[hour]["queryStoreHotspots"] += 1
    for row in read_csv(root / "sql_wait_stats_delta.csv"):
        wait_ms = _num(row.get("wait_time_ms"))
        if wait_ms > 0:
            buckets["run"]["waitMs"] += int(wait_ms)
            buckets["run"][str(row.get("wait_type") or "UNKNOWN")] += 1
    timeline = []
    for hour, values in sorted(buckets.items()):
        if hour == "run":
            continue
        total = sum(values.values())
        timeline.append({"hour": hour, "score": total, **dict(values)})
    peak = max(timeline, key=lambda x: x["score"], default={"hour": "n/a", "score": 0})
    return {"bucketCount": len(timeline), "peakHour": peak["hour"], "peakScore": peak["score"], "timeline": timeline, "waitSignals": dict(buckets.get("run", {}))}


def workload_fingerprinting(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = _evidence_root(evidence)
    families = Counter()
    signals: dict[str, list[str]] = defaultdict(list)
    for row in read_csv(root / "batch_tasks.csv"):
        text = " ".join(str(row.get(k, "")) for k in ("caption", "batch_group", "company"))
        family = _family_from_text(text)
        families[family] += 1
        if len(signals[family]) < 5:
            signals[family].append(str(row.get("caption") or row.get("batch_group") or "batch task"))
    for finding in findings:
        text = " ".join(finding.get("axContext", {}).get("tables", [])) + " " + finding.get("title", "")
        family = _family_from_text(text)
        families[family] += RANK.get(finding.get("severity"), 1)
        if len(signals[family]) < 5:
            signals[family].append(finding.get("id", "finding"))
    items = [{"family": family, "weight": count, "signals": signals[family]} for family, count in families.most_common()]
    return {"fingerprintCount": len(items), "dominantFamily": items[0]["family"] if items else "n/a", "items": items}


def archive_impact_sandbox(findings: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = retention_candidates(findings).get("candidates", [])
    scenarios = []
    for reduction in (10, 25, 50):
        scenario_items = []
        for item in candidates[:12]:
            signals = int(item.get("signals", 0))
            scenario_items.append({"table": item["table"], "reductionPercent": reduction, "estimatedRiskPointDrop": round(signals * reduction / 10, 1)})
        scenarios.append({"scenario": f"archive-{reduction}-percent-candidate-data", "candidateCount": len(scenario_items), "estimatedRiskPointDrop": round(sum(x["estimatedRiskPointDrop"] for x in scenario_items), 1), "tables": scenario_items})
    return {"scenarioCount": len(scenarios), "scenarios": scenarios}


def performance_budgeting(findings: list[dict[str, Any]]) -> dict[str, Any]:
    budgets = [
        {"metric": "critical_findings", "target": 0, "current": sum(1 for f in findings if f.get("severity") == "critical")},
        {"metric": "high_findings", "target": 5, "current": sum(1 for f in findings if f.get("severity") == "high")},
        {"metric": "blocking_findings", "target": 2, "current": sum(1 for f in findings if f.get("recommendation", {}).get("playbook") == "blocking-chain")},
        {"metric": "query_regression_findings", "target": 3, "current": sum(1 for f in findings if f.get("recommendation", {}).get("playbook") in {"deployment-regression", "parameter-sensitive-plan"})},
    ]
    for budget in budgets:
        budget["status"] = "fail" if budget["current"] > budget["target"] else "pass"
    return {"status": "fail" if any(b["status"] == "fail" for b in budgets) else "pass", "budgets": budgets}


def validation_orchestrator(findings: list[dict[str, Any]]) -> dict[str, Any]:
    steps = []
    for finding in _top(findings, 12):
        playbook = finding.get("recommendation", {}).get("playbook", "review")
        steps.append({
            "findingId": finding["id"],
            "title": finding["title"],
            "playbook": playbook,
            "preCheck": "Capture current SQL/AX evidence and export affected query/job baseline.",
            "testAction": f"Validate {playbook} remediation in TEST with identical time window or replay evidence.",
            "postCheck": "Compare duration, reads, waits, blocking time and batch overlap against baseline.",
            "acceptance": "Improves target metric by >=20% without new high-risk finding.",
        })
    return {"stepCount": len(steps), "steps": steps}


def operator_copilot_context(findings: list[dict[str, Any]], evidence: str | Path) -> dict[str, Any]:
    root = _evidence_root(evidence)
    files = {p.name: p.stat().st_size for p in root.glob("*.csv")}
    top_findings = [{"id": f["id"], "severity": f["severity"], "title": f["title"], "playbook": f.get("recommendation", {}).get("playbook")} for f in _top(findings, 8)]
    prompts = [
        "Welche Batch-Gruppen verursachen die hoechste Ueberschneidung im Peak-Fenster?",
        "Welche Query muss zuerst in TEST validiert werden und warum?",
        "Welche Evidenz fehlt, um X++ Attribution sicher zu machen?",
        "Welche Massnahme hat den besten Nutzen bei geringstem Produktionsrisiko?",
    ]
    return {"evidenceFiles": files, "topFindings": top_findings, "suggestedQuestions": prompts}


def self_calibrating_thresholds(evidence: str | Path) -> dict[str, Any]:
    root = _evidence_root(evidence)
    rows = read_csv(root / "query_store_runtime.csv")
    durations = sorted(_num(r.get("avg_duration_ms")) for r in rows if _num(r.get("avg_duration_ms")) > 0)
    reads = sorted(_num(r.get("avg_logical_io_reads")) for r in rows if _num(r.get("avg_logical_io_reads")) > 0)

    def percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, max(0, int(round((len(values) - 1) * pct))))
        return round(values[index], 2)

    return {
        "sampleCount": len(rows),
        "thresholds": [
            {"metric": "avg_duration_ms", "p90": percentile(durations, 0.90), "p95": percentile(durations, 0.95), "recommendedAlert": percentile(durations, 0.95)},
            {"metric": "avg_logical_io_reads", "p90": percentile(reads, 0.90), "p95": percentile(reads, 0.95), "recommendedAlert": percentile(reads, 0.95)},
        ],
    }


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
        "temporalHotspotMap": temporal_hotspot_map(evidence),
        "workloadFingerprinting": workload_fingerprinting(evidence, findings),
        "archiveImpactSandbox": archive_impact_sandbox(findings),
        "performanceBudgeting": performance_budgeting(findings),
        "validationOrchestrator": validation_orchestrator(findings),
        "operatorCopilotContext": operator_copilot_context(findings, evidence),
        "selfCalibratingThresholds": self_calibrating_thresholds(evidence),
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
