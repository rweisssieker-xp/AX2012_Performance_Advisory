from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import batch_collision_summary, load_evidence, parse_ax_datetime, write_json


SEV = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _num(value: Any, default: float = 0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _severity_rank(finding: dict[str, Any]) -> tuple[int, int, int]:
    return (
        SEV.get(str(finding.get("severity", "low")), 1),
        1 if finding.get("confidence") == "high" else 0,
        len(finding.get("evidence", [])),
    )


def _process_for_finding(finding: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(finding.get("title", "")),
            str(finding.get("likelyCause", "")),
            str(finding.get("recommendation", {}).get("summary", "")),
            " ".join(finding.get("axContext", {}).get("tables", []) or []),
            str(finding.get("axContext", {}).get("module", "")),
        ]
    ).upper()
    rules = [
        ("Inventory", ["INVENT", "LAGER", "ITEM", "MRP", "WAREHOUSE", "WMS"]),
        ("Finance", ["GENERALJOURNAL", "LEDGER", "CUSTTRANS", "VENDTRANS", "POSTING", "FIN"]),
        ("Sales", ["SALES", "CUST", "CUSTOMER"]),
        ("Purchasing", ["PURCH", "VEND", "VENDOR"]),
        ("Production", ["PROD", "BOM", "ROUTE"]),
        ("Integration", ["AIF", "SERVICE", "IMPORT", "EXPORT", "EDI", "LOG"]),
        ("Reporting", ["REPORT", "SSRS", "BI", "CUBE"]),
    ]
    for process, tokens in rules:
        if any(token in text for token in tokens):
            return process
    return "AX Core"


def _load_metadata(root: Path) -> dict[str, Any]:
    path = root / "metadata.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _batch_sla_forecast(batch_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"tasks": 0, "duration": 0.0, "late": 0, "hours": Counter()})
    for row in batch_rows:
        group = row.get("batch_group") or row.get("group") or "unknown"
        duration = _num(row.get("duration_seconds"))
        start = parse_ax_datetime(row.get("start_time"))
        end = parse_ax_datetime(row.get("end_time"))
        groups[group]["tasks"] += 1
        groups[group]["duration"] += duration
        if start:
            groups[group]["hours"][start.strftime("%H:00")] += 1
        if end and end.hour >= 7:
            groups[group]["late"] += 1
    forecast = []
    for group, item in groups.items():
        tasks = int(item["tasks"])
        avg = round(item["duration"] / max(1, tasks))
        late = int(item["late"])
        risk = min(100, late * 18 + int(avg / 600) * 8 + max(0, tasks - 10) * 2)
        forecast.append(
            {
                "batchGroup": group,
                "tasks": tasks,
                "avgDurationSeconds": avg,
                "lateAfter0700": late,
                "peakHour": item["hours"].most_common(1)[0][0] if item["hours"] else "unknown",
                "breachProbabilityPercent": risk,
                "owner": "AX Operations",
                "recommendation": "Move or split this group before business start." if risk >= 60 else "Monitor and validate after next run.",
            }
        )
    return sorted(forecast, key=lambda x: x["breachProbabilityPercent"], reverse=True)[:12]


def _write_board_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# CEO Board Report - AX Performance Advisor",
        "",
        f"Environment: `{payload.get('environment', 'unknown')}`",
        f"Executive risk: `{payload['executiveOverview']['riskBand']}`",
        f"Business impact EUR: `{payload['businessImpactEur']['lowEstimate']}` - `{payload['businessImpactEur']['highEstimate']}`",
        "",
        "## Executive Narrative",
        "",
        payload["ceoNarrativeAi"]["summary"],
        "",
        "## Decisions Required",
        "",
    ]
    for item in payload["decisionQueue"][:10]:
        lines.append(f"- **{item['priority']} {item['decision']}**: {item['recommendedAction']} Owner: {item['owner']} Deadline: {item['deadline']}")
    lines.extend(["", "## Risk Of Doing Nothing", ""])
    for item in payload["riskOfDoingNothing"]["timeline"]:
        lines.append(f"- {item['horizon']}: {item['risk']} - {item['message']}")
    lines.extend(["", "## Investment Justification", "", payload["investmentJustification"]["message"]])
    path.write_text("\n".join(lines), encoding="utf-8")


def generate_ceo_cockpit(
    evidence: str | Path,
    findings: list[dict[str, Any]],
    output: str | Path | None = None,
    trend_db: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(evidence)
    metadata = _load_metadata(root)
    batch_rows = _read_csv(root / "batch_tasks.csv")
    blocking_rows = _read_csv(root / "ax_live_blocking.csv") + _read_csv(root / "blocking.csv")
    session_rows = _read_csv(root / "user_sessions.csv")
    source_status = _read_csv(root / "source_status.csv")
    collision = batch_collision_summary(load_evidence(root))
    top = sorted(findings, key=_severity_rank, reverse=True)
    high = [f for f in findings if f.get("severity") in {"critical", "high"}]
    critical = [f for f in findings if f.get("severity") == "critical"]
    evidence_gaps = [row for row in source_status if str(row.get("status", "")).lower() not in {"ok", "present", "available"}]
    blocked = sum(1 for row in blocking_rows if str(row.get("blocking_session_id") or row.get("BlockingSessionId") or "").lower() not in {"", "0", "n/a", "none"})
    wide_inventory = sum(1 for row in blocking_rows if "INVENTSUM" in str(row.get("statement_text") or row.get("Query") or "").upper() and "INVENTDIM" in str(row.get("statement_text") or row.get("Query") or "").upper())
    health_score = max(0, 100 - len(critical) * 10 - (len(high) - len(critical)) * 4 - blocked * 5 - int(collision.get("collisionCount", 0)) // 3)
    risk_band = "red" if health_score < 45 else "amber" if health_score < 75 else "green"
    impact_low = int(len(high) * 1200 + blocked * 1800 + int(collision.get("collisionCount", 0)) * 350 + wide_inventory * 2500)
    impact_high = int(impact_low * 3.2 + max(0, 75 - health_score) * 1000)

    process_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"process": "", "findings": 0, "high": 0, "riskPoints": 0, "topIssues": Counter()})
    for finding in findings:
        process = _process_for_finding(finding)
        item = process_map[process]
        item["process"] = process
        item["findings"] += 1
        if finding.get("severity") in {"critical", "high"}:
            item["high"] += 1
        item["riskPoints"] += SEV.get(str(finding.get("severity", "low")), 1)
        item["topIssues"][finding.get("recommendation", {}).get("playbook") or finding.get("classification") or "review"] += 1
    process_heatmap = []
    for item in process_map.values():
        score = min(100, item["riskPoints"] * 7 + item["high"] * 12)
        process_heatmap.append(
            {
                "process": item["process"],
                "riskScore": score,
                "riskBand": "red" if score >= 70 else "amber" if score >= 35 else "green",
                "findings": item["findings"],
                "highFindings": item["high"],
                "dominantRisk": item["topIssues"].most_common(1)[0][0] if item["topIssues"] else "none",
                "businessOwner": f"{item['process']} Owner",
            }
        )
    process_heatmap = sorted(process_heatmap, key=lambda x: x["riskScore"], reverse=True)

    decision_queue = []
    for idx, finding in enumerate(top[:15], start=1):
        process = _process_for_finding(finding)
        sev = finding.get("severity", "medium")
        decision_queue.append(
            {
                "priority": f"P{1 if sev in {'critical', 'high'} else 2 if sev == 'medium' else 3}",
                "findingId": finding.get("id"),
                "decision": finding.get("title"),
                "process": process,
                "owner": finding.get("recommendation", {}).get("owner") or f"{process} Owner",
                "deadline": "next CAB / within 7 days" if sev in {"critical", "high"} else "next review cycle",
                "businessImpactEur": max(500, SEV.get(str(sev), 1) * 1200),
                "riskIfDeferred": "High operational recurrence risk." if sev in {"critical", "high"} else "May become recurring performance debt.",
                "recommendedAction": finding.get("recommendation", {}).get("summary") or "Review evidence and assign TEST validation.",
                "evidenceQuality": "high" if finding.get("confidence") == "high" and len(finding.get("evidence", [])) >= 2 else "needs-proof",
            }
        )

    no_action_risk = max(0, 100 - health_score + blocked * 4 + int(collision.get("peakConcurrency", 0)) * 3)
    timeline = [
        {"horizon": "7 days", "risk": min(100, no_action_risk), "message": "Recurring incidents likely in the same peak windows."},
        {"horizon": "30 days", "risk": min(100, no_action_risk + 18), "message": "Performance debt and support load increase if high findings stay open."},
        {"horizon": "90 days", "risk": min(100, no_action_risk + 35), "message": "Legacy stabilization becomes more expensive than controlled remediation."},
    ]
    portfolio = []
    for item in decision_queue[:20]:
        effort = "high" if item["evidenceQuality"] == "needs-proof" else "medium"
        lane = "Quick Win" if item["evidenceQuality"] == "high" and item["priority"] in {"P1", "P2"} else "Controlled Change" if item["priority"] == "P1" else "Strategic" if item["process"] in {"Inventory", "Finance"} else "Defer/Monitor"
        portfolio.append({**item, "effort": effort, "lane": lane})

    sla_forecast = _batch_sla_forecast(batch_rows)
    legacy_pressure = min(100, len(findings) + len(evidence_gaps) * 5 + len(batch_rows) // 25 + max(0, 20 - len(source_status)))
    structural = len([p for p in process_heatmap if p["riskBand"] == "red"]) + (1 if legacy_pressure >= 70 else 0)
    tactical = len([d for d in decision_queue if d["evidenceQuality"] == "high"])
    migration_signal = "tune-first" if tactical >= structural else "modernization-pressure"
    stability = max(0, min(100, health_score - len(evidence_gaps) * 3 + (10 if blocked == 0 else -10)))
    crisis_active = risk_band == "red" or blocked > 0 or int(collision.get("peakConcurrency", 0)) >= 10
    customer_signal = {
        "status": "inferred-from-technical-evidence",
        "affectedProcesses": [p["process"] for p in process_heatmap[:4]],
        "riskMessage": "Customer/order impact cannot be proven without process SLA or ticket data, but affected AX domains indicate where business disruption is most likely.",
        "nextEvidence": "Add service desk incident export, order backlog KPIs or batch SLA contracts for direct customer impact proof.",
    }
    payload = {
        "featureCount": 15,
        "writePolicy": "local-files-only-no-db-writes",
        "environment": metadata.get("environment") or metadata.get("server") or root.name,
        "executiveOverview": {
            "healthScore": health_score,
            "riskBand": risk_band,
            "highCriticalFindings": len(high),
            "batchCollisionCount": collision.get("collisionCount", 0),
            "peakConcurrency": collision.get("peakConcurrency", 0),
            "blockedRows": blocked,
            "decisionCount": len(decision_queue),
        },
        "businessImpactEur": {
            "lowEstimate": impact_low,
            "highEstimate": impact_high,
            "assumption": "Directional local estimate from high findings, blocking rows, batch collisions and broad inventory impact. Replace with real hourly cost model when available.",
        },
        "decisionQueue": decision_queue,
        "riskOfDoingNothing": {"score": min(100, no_action_risk), "timeline": timeline},
        "operationalOwnership": {
            "owners": [{"owner": owner, "openDecisions": count} for owner, count in Counter(d["owner"] for d in decision_queue).most_common()],
            "unassignedCount": sum(1 for d in decision_queue if not d.get("owner")),
        },
        "businessProcessHeatmap": process_heatmap,
        "axLegacyRiskIndex": {
            "score": legacy_pressure,
            "riskBand": "red" if legacy_pressure >= 70 else "amber" if legacy_pressure >= 40 else "green",
            "supportMessage": "AX 2012 / SQL Server 2016 legacy operation needs explicit stabilization, evidence and modernization governance.",
            "migrationSignal": migration_signal,
        },
        "slaBreachForecast": {"items": sla_forecast, "highestProbabilityPercent": sla_forecast[0]["breachProbabilityPercent"] if sla_forecast else 0},
        "changePortfolioView": {"items": portfolio, "laneCounts": dict(Counter(item["lane"] for item in portfolio))},
        "boardReadyMonthlyReport": {
            "title": "AX Performance CEO Monthly Brief",
            "sections": ["Executive Narrative", "Decisions Required", "Risk Of Doing Nothing", "Investment Justification"],
            "localReport": "",
        },
        "customerOrderImpactSignal": customer_signal,
        "stabilityConfidenceScore": {
            "score": stability,
            "band": "green" if stability >= 75 else "amber" if stability >= 45 else "red",
            "drivers": ["evidence completeness", "open high findings", "blocking pressure", "batch peak pressure"],
        },
        "investmentJustification": {
            "recommendedPosture": "stabilize-and-modernize" if migration_signal != "tune-first" else "targeted-tuning-first",
            "message": f"Expected avoidable impact range is EUR {impact_low:,} - {impact_high:,}. Prioritize governed remediation where evidence quality is high, and collect missing proof before expensive changes.",
            "estimatedAvoidablePercent": 35 if health_score < 60 else 20,
        },
        "crisisMode": {
            "active": crisis_active,
            "triggers": [t for t, active in [("red risk band", risk_band == "red"), ("live blocking", blocked > 0), ("high batch peak", int(collision.get("peakConcurrency", 0)) >= 10), ("wide inventory query", wide_inventory > 0)] if active],
            "firstActions": ["Freeze non-essential batch changes", "Validate live blockers read-only", "Prioritize P1 decision queue", "Communicate status to process owners"] if crisis_active else ["Continue daily monitoring"],
        },
        "ceoNarrativeAi": {
            "summary": f"AX performance risk is {risk_band}. There are {len(high)} high/critical findings, {collision.get('collisionCount', 0)} batch collisions and {blocked} blocked rows in the current evidence.",
            "boardAsk": "Approve focused TEST validation and owner assignment for P1/P2 decisions.",
            "nextQuestion": "Which business process owner accepts the risk if the top P1 actions are deferred?",
        },
    }
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_path = output_path.with_name("ceo-board-report.md")
        payload["boardReadyMonthlyReport"]["localReport"] = str(report_path)
        write_json(output_path, payload)
        _write_board_report(report_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate CEO cockpit from local AXPA evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    from axpa_core import analyze_evidence

    payload = generate_ceo_cockpit(args.evidence, analyze_evidence(args.evidence), args.output)
    print(f"Wrote CEO cockpit with {payload['featureCount']} features to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
