from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, module_health_scores, write_json


SEV = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _run_id(evidence: str | Path) -> str:
    root = Path(evidence)
    metadata = root / "metadata.json"
    if metadata.exists():
        try:
            data = json.loads(metadata.read_text(encoding="utf-8"))
            return str(data.get("runId") or data.get("timestamp") or root.name)
        except json.JSONDecodeError:
            pass
    return f"{root.name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def update_time_series_store(evidence: str | Path, db: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    root = Path(evidence)
    run_id = _run_id(root)
    db_path = Path(db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    severity = Counter(f.get("severity", "unknown") for f in findings)
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    modules = module_health_scores(findings)
    query_rows = _read_csv(root / "sql_top_queries.csv")
    wait_rows = _read_csv(root / "sql_wait_stats.csv")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY, collected_at TEXT, evidence TEXT, finding_count INTEGER,
                high_count INTEGER, health_score INTEGER
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS metrics (
                run_id TEXT, metric_type TEXT, metric_name TEXT, metric_value REAL, label TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS findings (
                run_id TEXT, finding_id TEXT, severity TEXT, playbook TEXT, module TEXT, title TEXT
            )"""
        )
        high_count = severity["high"] + severity["critical"]
        health = max(0, 100 - min(100, sum(SEV.get(f.get("severity"), 1) for f in findings)))
        conn.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?, ?, ?)", (run_id, _now(), str(root), len(findings), high_count, health))
        conn.execute("DELETE FROM metrics WHERE run_id=?", (run_id,))
        conn.execute("DELETE FROM findings WHERE run_id=?", (run_id,))
        for name, value in severity.items():
            conn.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (run_id, "severity", name, float(value), "findings"))
        for name, value in playbooks.items():
            conn.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (run_id, "playbook", name, float(value), "findings"))
        for name, value in modules.items():
            conn.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (run_id, "module_health", name, float(value.get("score", 0)), value.get("risk", "")))
        for row in query_rows[:50]:
            metric = row.get("total_logical_reads") or row.get("logical_reads") or row.get("total_worker_time") or "0"
            conn.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (run_id, "query", row.get("query_hash", row.get("queryHash", "unknown")), float(metric or 0), row.get("database_name", "")))
        for row in wait_rows[:80]:
            metric = row.get("wait_time_ms") or row.get("waitTimeMs") or row.get("waiting_tasks_count") or "0"
            conn.execute("INSERT INTO metrics VALUES (?, ?, ?, ?, ?)", (run_id, "wait", row.get("wait_type", row.get("waitType", "unknown")), float(metric or 0), "sql"))
        conn.executemany(
            "INSERT INTO findings VALUES (?, ?, ?, ?, ?, ?)",
            [(run_id, f["id"], f["severity"], f.get("recommendation", {}).get("playbook", ""), f.get("axContext", {}).get("module", "Unknown"), f["title"]) for f in findings],
        )
        conn.commit()
    return {"db": str(db_path), "runId": run_id, "findings": len(findings), "highCount": high_count, "healthScore": health}


def build_alerts(evidence: str | Path, trend_db: str | Path | None = None) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    alerts = []
    for finding in findings:
        sev = finding.get("severity")
        if sev not in {"critical", "high"}:
            continue
        alerts.append(
            {
                "alertId": f"ALERT-{finding['id']}",
                "severity": sev,
                "title": finding["title"],
                "route": "DBA" if finding.get("sqlContext", {}).get("waitTypes") else "AX Operations",
                "status": "open",
                "silenceKey": f"{finding.get('recommendation', {}).get('playbook', 'review')}:{finding.get('axContext', {}).get('module', 'Unknown')}",
                "acknowledgeRequired": True,
                "evidence": [e.get("source", "") for e in finding.get("evidence", [])[:3]],
                "nextAction": finding.get("recommendation", {}).get("summary", ""),
            }
        )
    if trend_db and Path(trend_db).exists():
        with sqlite3.connect(trend_db) as conn:
            rows = conn.execute("SELECT run_id, high_count FROM runs ORDER BY collected_at DESC LIMIT 5").fetchall()
        if len(rows) >= 2 and rows[0][1] > rows[-1][1]:
            alerts.append({"alertId": "ALERT-TREND-HIGH-RISK", "severity": "medium", "title": "High-risk finding trend increased", "route": "AX Operations", "status": "open", "silenceKey": "trend:high-risk", "acknowledgeRequired": False, "evidence": [str(rows)], "nextAction": "Review trend increase and recent changes."})
    return {"alertCount": len(alerts), "alerts": alerts}


def build_estate_inventory(evidence_paths: list[str | Path]) -> dict[str, Any]:
    environments = []
    totals = Counter()
    for evidence in evidence_paths:
        root = Path(evidence)
        findings = analyze_evidence(root)
        config = {}
        cfg = root / "config.json"
        if cfg.exists():
            try:
                config = json.loads(cfg.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                config = {}
        severity = Counter(f.get("severity", "unknown") for f in findings)
        totals.update(severity)
        environments.append(
            {
                "name": root.name,
                "path": str(root),
                "sqlServer": config.get("sqlServer", config.get("server", "unknown")),
                "axDatabase": config.get("axDatabase", config.get("database", "unknown")),
                "findingCount": len(findings),
                "highCount": severity["high"] + severity["critical"],
                "modules": module_health_scores(findings),
                "tags": ["AX2012", "SQL2016", "read-only"],
            }
        )
    return {"environmentCount": len(environments), "severityTotals": dict(totals), "environments": environments}


def build_plan_repository(evidence: str | Path, output_dir: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    query_rows = _read_csv(root / "sql_top_queries.csv")
    qs_rows = _read_csv(root / "query_store_runtime.csv")
    entries = []
    for source, rows in [("sql_top_queries", query_rows), ("query_store_runtime", qs_rows)]:
        for row in rows[:100]:
            query_hash = row.get("query_hash") or row.get("queryHash") or row.get("query_id") or row.get("queryId") or "unknown"
            plan_hash = row.get("query_plan_hash") or row.get("planHash") or row.get("plan_id") or row.get("planId") or ""
            entry = {
                "source": source,
                "queryHash": query_hash,
                "planHash": plan_hash,
                "duration": row.get("avg_duration") or row.get("duration_ms") or row.get("total_elapsed_time") or "",
                "cpu": row.get("avg_cpu_time") or row.get("total_worker_time") or "",
                "reads": row.get("total_logical_reads") or row.get("logical_reads") or "",
                "database": row.get("database_name") or row.get("databaseName") or "",
            }
            entries.append(entry)
    grouped = defaultdict(list)
    for entry in entries:
        grouped[entry["queryHash"]].append(entry)
    regressions = []
    for query_hash, plans in grouped.items():
        distinct_plans = {p["planHash"] for p in plans if p["planHash"]}
        if len(distinct_plans) > 1:
            regressions.append({"queryHash": query_hash, "planCount": len(distinct_plans), "risk": "plan-variance", "plans": list(distinct_plans)[:10]})
    payload = {"entryCount": len(entries), "queryFamilies": len(grouped), "regressionCandidates": regressions, "entries": entries[:250]}
    write_json(out / "plan-repository.json", payload)
    return payload


def build_notifications(alerts: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    teams = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "AXPA alerts",
        "themeColor": "B42318" if any(a["severity"] in {"critical", "high"} for a in alerts["alerts"]) else "B45309",
        "sections": [{"activityTitle": a["title"], "facts": [{"name": "Severity", "value": a["severity"]}, {"name": "Route", "value": a["route"]}, {"name": "Next", "value": a["nextAction"]}]} for a in alerts["alerts"][:10]],
    }
    service_now = [
        {"short_description": a["title"], "severity": a["severity"], "assignment_group": a["route"], "comments": a["nextAction"], "correlation_id": a["alertId"]}
        for a in alerts["alerts"]
    ]
    pagerduty = [
        {"routing_key": "CONFIGURE_ME", "event_action": "trigger", "payload": {"summary": a["title"], "severity": "error" if a["severity"] in {"critical", "high"} else "warning", "source": "AXPA", "custom_details": a}}
        for a in alerts["alerts"][:20]
    ]
    write_json(out / "teams-card.json", teams)
    write_json(out / "servicenow-incidents.json", service_now)
    write_json(out / "pagerduty-events.json", pagerduty)
    return {"teams": str(out / "teams-card.json"), "serviceNow": str(out / "servicenow-incidents.json"), "pagerDuty": str(out / "pagerduty-events.json"), "notificationCount": len(alerts["alerts"])}


def competitor_coverage() -> dict[str, Any]:
    return {
        "covered": [
            "SQL/AX evidence collection",
            "query/wait/finding analysis",
            "dashboard and reports",
            "Power BI/ticket/evidence exports",
            "admin execution preview workflow",
            "time-series store",
            "alert generation",
            "fleet inventory",
            "plan repository",
            "notification payload exports",
            "AX-specific business context",
        ],
        "differentiators": [
            "AX 2012 table/batch/process-aware recommendations",
            "GxP/ITIL evidence and approval gates",
            "Admin execution tokens with no blind PROD changes",
            "Trace Parser/DynamicsPerf evidence gaps surfaced explicitly",
        ],
        "requiresExternalConfig": ["Teams webhook", "ServiceNow API", "PagerDuty routing key", "Jira/Azure DevOps credentials", "Power BI workspace/dataset"],
    }


def generate_enterprise_pack(evidence: str | Path, output_dir: str | Path, estate: list[str] | None = None) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    trend = update_time_series_store(evidence, out / "axpa-trends.sqlite")
    alerts = build_alerts(evidence, out / "axpa-trends.sqlite")
    inventory = build_estate_inventory(estate or [evidence])
    plan_repo = build_plan_repository(evidence, out / "plan-repository")
    notifications = build_notifications(alerts, out / "notifications")
    payload = {
        "generatedAt": _now(),
        "timeSeriesStore": trend,
        "alerts": alerts,
        "estateInventory": inventory,
        "planRepository": {k: v for k, v in plan_repo.items() if k != "entries"},
        "notifications": notifications,
        "competitorCoverage": competitor_coverage(),
    }
    write_json(out / "enterprise-observability-pack.json", payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA enterprise observability pack.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--estate", nargs="*")
    args = parser.parse_args()
    payload = generate_enterprise_pack(args.evidence, args.output_dir, args.estate)
    print(f"Wrote enterprise observability pack to {args.output_dir}")
    print(f"Alerts: {payload['alerts']['alertCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
