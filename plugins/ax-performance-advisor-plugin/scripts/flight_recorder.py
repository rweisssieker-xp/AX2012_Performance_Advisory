from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axpa_core import _frontend_broad_inventory_signature

_csv_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_csv_limit)
        break
    except OverflowError:
        _csv_limit = int(_csv_limit / 10)


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def num(value: Any, default: float = 0) -> float:
    try:
        if value in (None, ""):
            return default
        if isinstance(value, str):
            text = value.strip()
            if "," in text and "." in text:
                text = text.replace(".", "").replace(",", ".")
            elif "," in text:
                text = text.replace(",", ".")
            return float(text)
        return float(value)
    except (TypeError, ValueError):
        return default


def snapshot_dir(source_evidence: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = output_dir / stamp
    shutil.copytree(source_evidence, target, dirs_exist_ok=True)
    return target


def classify_statement(statement: str) -> dict[str, Any]:
    text = str(statement or "")
    upper = text.upper()
    sig = _frontend_broad_inventory_signature(text)
    if sig["isInventoryWideQuery"]:
        return {
            "family": "wide-inventory-frontend",
            "businessProcess": "Inventory availability / on-hand",
            "confidence": "high",
            "details": sig,
        }
    table_map = [
        ("GENERALJOURNALACCOUNTENTRY", "finance-posting", "Finance posting"),
        ("GENERALJOURNALENTRY", "finance-posting", "Finance posting"),
        ("CUSTTRANS", "customer-balance", "Accounts receivable"),
        ("VENDTRANS", "vendor-balance", "Accounts payable"),
        ("SALESLINE", "sales-order", "Sales order"),
        ("PURCHLINE", "purchase-order", "Purchase order"),
        ("WHS", "warehouse", "Warehouse"),
        ("BATCH", "batch-framework", "Batch framework"),
    ]
    for token, family, process in table_map:
        if token in upper:
            return {"family": family, "businessProcess": process, "confidence": "medium", "details": {}}
    return {"family": "unknown-ax-sql", "businessProcess": "Unknown", "confidence": "low", "details": {}}


def stable_signature(row: dict[str, Any]) -> str:
    raw = "|".join(str(row.get(k, "")) for k in ["family", "businessProcess", "host", "user", "sessionId", "queryHash", "statementSample"])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12].upper()


def infer_form(row: dict[str, Any]) -> dict[str, Any]:
    sample = str(row.get("statementSample") or "").upper()
    family = str(row.get("family") or "")
    candidates: list[dict[str, Any]] = []
    if family == "wide-inventory-frontend":
        candidates.extend([
            {"form": "InventOnHand", "confidence": 82, "why": "InventSum/InventDim availability aggregation with multiple dimensions."},
            {"form": "InventAvailability", "confidence": 74, "why": "Availability fields and InventDim filters are present."},
            {"form": "WHS reservation/availability", "confidence": 68, "why": "Warehouse/location/status dimensions are present."},
            {"form": "custom inventory inquiry", "confidence": 55, "why": "Pattern can also be triggered by custom stock lookup code."},
        ])
    elif "GENERALJOURNAL" in sample:
        candidates.append({"form": "Ledger journal posting/status", "confidence": 70, "why": "General journal tables are present."})
    elif "SALESLINE" in sample:
        candidates.append({"form": "SalesTable/SalesLine", "confidence": 70, "why": "Sales order line table is present."})
    elif "PURCHLINE" in sample:
        candidates.append({"form": "PurchTable/PurchLine", "confidence": 70, "why": "Purchase order line table is present."})
    elif "WHS" in sample:
        candidates.append({"form": "Warehouse management form", "confidence": 65, "why": "WHS table family is present."})
    return {"candidates": candidates, "best": candidates[0] if candidates else {"form": "unknown", "confidence": 0, "why": "No form-level trace evidence available."}}


def spid_session_confidence(row: dict[str, Any]) -> dict[str, Any]:
    score = 0
    reasons = []
    if row.get("sessionId"):
        score += 30
        reasons.append("SQL session id present")
    if row.get("user"):
        score += 25
        reasons.append("AX/SQL login present")
    if row.get("host"):
        score += 20
        reasons.append("host/AOS present")
    if row.get("queryHash"):
        score += 15
        reasons.append("query hash present")
    if row.get("family") != "unknown-ax-sql":
        score += 10
        reasons.append("AX business SQL pattern classified")
    return {"score": min(score, 100), "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D", "reasons": reasons}


def collect_rows(evidence_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source, path in [
        ("ax_live_blocking", evidence_dir / "ax_live_blocking.csv"),
        ("sql_top_queries", evidence_dir / "sql_top_queries.csv"),
        ("blocking", evidence_dir / "blocking.csv"),
    ]:
        for row in read_csv(path):
            statement = str(row.get("statement_text") or row.get("Query") or "")
            cls = classify_statement(statement)
            logical_reads = num(row.get("logical_reads") or row.get("total_logical_reads") or row.get("reads"))
            elapsed_ms = num(row.get("elapsed_time_ms") or row.get("avg_duration_ms") or row.get("total_duration_ms"))
            cpu_ms = num(row.get("cpu_time_ms") or row.get("total_cpu_ms"))
            wait_ms = num(row.get("wait_time_ms") or row.get("waitMs"))
            pressure = logical_reads + elapsed_ms * 1000 + cpu_ms * 500 + wait_ms * 500
            if pressure <= 0:
                continue
            item = {
                "source": source,
                "checkTime": row.get("check_time") or row.get("last_execution_time") or row.get("CheckDate") or "",
                "user": row.get("user_id") or row.get("UserId") or "",
                "host": row.get("host_name") or row.get("HostName") or "",
                "sessionId": row.get("session_id") or row.get("SessionId") or "",
                "blockingSessionId": row.get("blocking_session_id") or row.get("BlockingSessionId") or "",
                "waitType": row.get("wait_type") or row.get("waitType") or "",
                "queryHash": row.get("query_hash") or "",
                "family": cls["family"],
                "businessProcess": cls["businessProcess"],
                "confidence": cls["confidence"],
                "logicalReads": int(logical_reads),
                "elapsedMs": int(elapsed_ms),
                "cpuMs": int(cpu_ms),
                "waitMs": int(wait_ms),
                "pressureScore": round(pressure, 2),
                "statementSample": statement[:500],
                "classificationDetails": cls["details"],
            }
            item["signature"] = stable_signature(item)
            item["formInference"] = infer_form(item)
            item["spidAxSessionConfidence"] = spid_session_confidence(item)
            rows.append(item)
    return sorted(rows, key=lambda r: r["pressureScore"], reverse=True)


def _matches_complaint(row: dict[str, Any], user: str = "", host: str = "", text: str = "") -> bool:
    haystack = json.dumps(row, ensure_ascii=False).lower()
    checks = [value.lower() for value in [user, host, text] if value]
    return all(value in haystack for value in checks) if checks else True


def _aos_pressure(evidence_dir: Path) -> dict[str, Any]:
    rows = read_csv(evidence_dir / "aos_counters.csv")
    hot = []
    for row in rows:
        path = str(row.get("Path") or row.get("path") or "")
        value = num(row.get("CookedValue") or row.get("cookedvalue"))
        lower = path.lower()
        risk = "green"
        if "% processor time" in lower and value >= 85:
            risk = "red"
        elif "available mbytes" in lower and value <= 1024:
            risk = "red"
        elif "avg. disk sec" in lower and value >= 0.05:
            risk = "amber"
        if risk != "green":
            hot.append({"path": path, "value": round(value, 3), "risk": risk})
    return {"rowCount": len(rows), "hotCounters": hot[:20], "status": "red" if any(x["risk"] == "red" for x in hot) else "amber" if hot else "green" if rows else "missing"}


def _event_correlation(evidence_dir: Path) -> dict[str, Any]:
    rows = read_csv(evidence_dir / "ax_events.csv")
    filtered = []
    for row in rows:
        msg = str(row.get("Message") or row.get("message") or "")
        level = str(row.get("LevelDisplayName") or row.get("level") or "")
        if any(token in msg.upper() for token in ["TIMEOUT", "DEADLOCK", "BLOCK", "SLOW", "ERROR", "RPC", "AOS", "BATCH"]):
            filtered.append({
                "time": row.get("TimeCreated") or row.get("time") or "",
                "provider": row.get("ProviderName") or "",
                "level": level,
                "message": msg[:500],
            })
    return {"rowCount": len(rows), "signalCount": len(filtered), "signals": filtered[:25]}


def _query_store_delta(evidence_dir: Path, flight_rows: list[dict[str, Any]]) -> dict[str, Any]:
    qs_rows = read_csv(evidence_dir / "query_store_runtime.csv")
    if not qs_rows:
        return {"status": "missing", "rowCount": 0, "hotspots": []}
    hashes = {str(r.get("queryHash") or "").lower() for r in flight_rows if r.get("queryHash")}
    hotspots = []
    for row in qs_rows:
        query_id = str(row.get("query_id") or row.get("queryId") or "")
        avg_ms = num(row.get("avg_duration_ms") or row.get("avgDurationMs"))
        reads = num(row.get("avg_logical_io_reads") or row.get("avg_reads") or row.get("avgReads"))
        text = json.dumps(row).lower()
        related = any(h and h in text for h in hashes)
        if related or avg_ms >= 5_000 or reads >= 100_000:
            hotspots.append({
                "queryId": query_id,
                "planId": row.get("plan_id") or row.get("planId") or "",
                "avgDurationMs": round(avg_ms, 2),
                "avgReads": round(reads, 2),
                "relatedToFlightRow": related,
                "recommendation": "Compare this Query Store row against baseline and validate whether it aligns with the complaint window.",
            })
    return {"status": "active", "rowCount": len(qs_rows), "hotspots": sorted(hotspots, key=lambda x: (x["relatedToFlightRow"], x["avgDurationMs"], x["avgReads"]), reverse=True)[:25]}


def _known_pattern_learning(evidence_dir: Path, rows: list[dict[str, Any]], known_patterns: Path | None = None) -> dict[str, Any]:
    path = known_patterns or (evidence_dir / "known_frontend_patterns.json")
    patterns = []
    if path.exists():
        try:
            patterns = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            patterns = []
    seeds = []
    for row in rows[:25]:
        signature = row.get("signature") or f"{row.get('family')}|{row.get('businessProcess')}|{row.get('host')}|{row.get('queryHash')}"
        matched = [p for p in patterns if str(p.get("family", "")).lower() == str(row.get("family", "")).lower() or str(p.get("queryHash", "")).lower() == str(row.get("queryHash", "")).lower()]
        seeds.append({
            "signature": signature,
            "family": row.get("family"),
            "queryHash": row.get("queryHash"),
            "suggestedLabel": "InventOnHand all dimensions" if row.get("family") == "wide-inventory-frontend" else row.get("businessProcess"),
            "form": row.get("formInference", {}).get("best", {}).get("form", "unknown"),
            "matchCount": len(matched),
            "nextAction": "Confirm label after incident review; store it in known_frontend_patterns.json to improve future attribution.",
        })
    return {"patternFile": str(path), "knownPatternCount": len(patterns), "seeds": seeds[:20]}


def read_feedback(store: Path | None) -> list[dict[str, Any]]:
    if not store or not store.exists():
        return []
    try:
        return json.loads(store.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def write_feedback(store: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = read_feedback(store)
    entry = {**entry, "recordedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    rows.append(entry)
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    return rows


def _feedback_summary(rows: list[dict[str, Any]], feedback_store: Path | None) -> dict[str, Any]:
    feedback = read_feedback(feedback_store)
    by_sig = {str(item.get("signature")): item for item in feedback}
    applied = []
    for row in rows[:50]:
        if row.get("signature") in by_sig:
            applied.append({"signature": row.get("signature"), **by_sig[row.get("signature")]})
    return {
        "store": str(feedback_store) if feedback_store else "",
        "entryCount": len(feedback),
        "appliedCount": len(applied),
        "decisions": [{"decision": k, "count": v} for k, v in Counter(str(x.get("decision", "unknown")) for x in feedback).most_common()],
        "applied": applied[:20],
    }


def _frontend_extra_analyzers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    report = []
    personalization = []
    security = []
    for row in rows:
        text = str(row.get("statementSample") or "").upper()
        if any(token in text for token in ["SRS", "SSRS", "PRINT", "PRINTMGT", "DOCU", "DOCUMENT"]):
            report.append({"signature": row.get("signature"), "user": row.get("user"), "host": row.get("host"), "reason": "Report/print/document SQL pattern", "pressureScore": row.get("pressureScore")})
        if row.get("user") and row.get("host") and row.get("family") == "unknown-ax-sql" and row.get("pressureScore", 0) > 10_000_000:
            personalization.append({"signature": row.get("signature"), "user": row.get("user"), "host": row.get("host"), "reason": "User-specific high pressure with unknown SQL family; check usage data, saved filters and personalization."})
        if any(token in text for token in ["SECURITYPOLICY", "XDS", "EXISTS", "DATAAREAID"]) and text.count("EXISTS") >= 2:
            security.append({"signature": row.get("signature"), "family": row.get("family"), "reason": "Multiple EXISTS/DataAreaId predicates can indicate security/role/query inflation.", "pressureScore": row.get("pressureScore")})
    return {
        "reportPrintAnalyzer": {"count": len(report), "items": report[:20]},
        "personalizationUsageDataRisk": {"count": len(personalization), "items": personalization[:20]},
        "securityRoleQueryInflation": {"count": len(security), "items": security[:20]},
    }


def _incident_one_pager(payload: dict[str, Any]) -> str:
    top = payload.get("topRows", [])[:5]
    lines = [
        "# AX Frontend Incident One-Pager",
        "",
        f"Generated: {payload.get('generatedAt')}",
        f"Evidence: `{payload.get('evidence')}`",
        "",
        "## Summary",
        f"- Flight rows: {payload.get('rowCount', 0)}",
        f"- Wide inventory frontend rows: {payload.get('wideInventoryCount', 0)}",
        f"- Blocking rows: {payload.get('blockingRows', 0)}",
        f"- Complaint decision: {payload.get('complaintWizard', {}).get('decision', 'n/a')}",
        "",
        "## Top Suspects",
    ]
    for row in top:
        form = row.get("formInference", {}).get("best", {})
        conf = row.get("spidAxSessionConfidence", {})
        lines.append(f"- {row.get('family')} | user `{row.get('user') or 'unknown'}` | host `{row.get('host') or 'unknown'}` | session `{row.get('sessionId')}` | pressure `{row.get('pressureScore')}` | form `{form.get('form')}` ({form.get('confidence')}%) | match {conf.get('grade')}/{conf.get('score')}")
    lines.extend([
        "",
        "## Immediate Operator Actions",
        "- Confirm whether the user action was intentional.",
        "- If accidental, stop/narrow only through approved operations procedure.",
        "- Re-run a 5-minute server-side flight recording if the issue is still active.",
        "- Save operator feedback so future incidents are recognized faster.",
    ])
    return "\n".join(lines) + "\n"


def _complaint_wizard(rows: list[dict[str, Any]], user: str = "", host: str = "", text: str = "") -> dict[str, Any]:
    matches = [r for r in rows if _matches_complaint(r, user, host, text)]
    if not matches and (user or host or text):
        matches = rows[:10]
    questions = [
        "Which user reported the slow frontend and at what exact time?",
        "Which AX form/menu item was open?",
        "Was an all-dimensions/on-hand inquiry intentional?",
        "Did other users on the same AOS/host report slowness?",
        "Can the action be repeated with restrictive filters in TEST?",
    ]
    return {
        "input": {"user": user, "host": host, "text": text},
        "matchCount": len(matches),
        "topMatches": matches[:15],
        "nextQuestions": questions,
        "decision": "wide-inventory-likely" if any(r.get("family") == "wide-inventory-frontend" for r in matches) else "needs-more-context",
    }


def build_report(evidence_dir: Path, output: Path | None = None, complaint_user: str = "", complaint_host: str = "", complaint_text: str = "", known_patterns: Path | None = None, feedback_store: Path | None = None, markdown_output: Path | None = None) -> dict[str, Any]:
    rows = collect_rows(evidence_dir)
    top = rows[:50]
    blockers = [r for r in rows if str(r.get("blockingSessionId") or "").lower() not in {"", "0", "n/a", "none"}]
    wide = [r for r in rows if r["family"] == "wide-inventory-frontend"]
    extras = _frontend_extra_analyzers(rows)
    payload = {
        "mode": "server-side-lightweight-flight-recorder",
        "evidence": str(evidence_dir),
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "rowCount": len(rows),
        "topRows": top,
        "wideInventoryCount": len(wide),
        "blockingRows": len(blockers),
        "families": [{"family": k, "count": v} for k, v in Counter(r["family"] for r in rows).most_common()],
        "hosts": [{"host": k or "unknown", "count": v} for k, v in Counter(r["host"] for r in rows).most_common(12)],
        "users": [{"user": k or "unknown", "count": v} for k, v in Counter(r["user"] for r in rows).most_common(12)],
        "waits": [{"waitType": k or "none", "count": v} for k, v in Counter(r["waitType"] for r in rows).most_common(12)],
        "timeline": [
            {
                "time": r["checkTime"],
                "signal": r["family"],
                "user": r["user"] or "unknown",
                "host": r["host"] or "unknown",
                "pressureScore": r["pressureScore"],
                "nextQuestion": "Map this SQL/session to the AX user action and confirm whether it is intentional.",
            }
            for r in top[:25]
        ],
        "collectorPlan": {
            "intervalSeconds": 5,
            "durationMinutes": 5,
            "internalSqlCollector": "collect_sql_live_snapshot.ps1",
            "liveCommand": "powershell scripts/collect_lightweight_flight_recorder.ps1 -ConnectionString <readonly-sql-connection> -OutputDirectory out\\flight-live -AxDatabaseName MicrosoftDynamicsGBLAX -AosComputerName <AOS> -IntervalSeconds 5 -Samples 12 -IncludeAosCounters -IncludeEvents -IncludeQueryStore",
            "sources": [
                "sys.dm_exec_requests/sessions/sql_text",
                "sys.dm_os_waiting_tasks",
                "sys.dm_tran_locks",
                "sys.dm_exec_query_stats recent AX SQL",
                "AX user sessions",
                "AOS Windows counters",
                "Event log warnings/errors",
                "Query Store runtime if enabled",
            ],
            "excludedHeavyCollectors": [
                "sys.dm_db_index_physical_stats",
                "sys.dm_db_stats_properties full inventory",
                "Trace Parser client capture",
                "SQL Profiler trace",
            ],
            "safety": "Read-only lightweight live snapshots; no index fragmentation, no stats scan, no client agent, no Trace Parser, no SQL Profiler.",
        },
        "aosPressure": _aos_pressure(evidence_dir),
        "eventCorrelation": _event_correlation(evidence_dir),
        "queryStoreDelta": _query_store_delta(evidence_dir, rows),
        "knownPatternLearning": _known_pattern_learning(evidence_dir, rows, known_patterns),
        "operatorFeedbackStore": _feedback_summary(rows, feedback_store),
        "complaintWizard": _complaint_wizard(rows, complaint_user, complaint_host, complaint_text),
        "formInferenceEngine": {"top": [{"signature": r.get("signature"), "family": r.get("family"), "best": r.get("formInference", {}).get("best"), "confidence": r.get("spidAxSessionConfidence")} for r in top[:25]]},
        "spidAxSessionConfidence": {"averageScore": round(sum(r.get("spidAxSessionConfidence", {}).get("score", 0) for r in top) / max(1, len(top)), 2), "rows": [{"signature": r.get("signature"), **r.get("spidAxSessionConfidence", {})} for r in top[:25]]},
        **extras,
        "operatorActions": [
            {"action": "mark-intentional", "effect": "Suppress as expected heavy inquiry for this user/time window after owner confirmation."},
            {"action": "mark-false-positive", "effect": "Adds feedback for future known-pattern learning."},
            {"action": "create-ticket", "effect": "Turns matched rows into ADO/Jira/ServiceNow draft when push credentials exist."},
            {"action": "watch-next-5-min", "effect": "Run the live collector again with five-second samples."},
        ],
    }
    payload["incidentOnePager"] = _incident_one_pager(payload)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(payload["incidentOnePager"], encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="AX lightweight server-side flight recorder.")
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="Copy existing evidence snapshots on an interval.")
    record.add_argument("--source-evidence", required=True)
    record.add_argument("--output-dir", required=True)
    record.add_argument("--interval-seconds", type=int, default=300)
    record.add_argument("--samples", type=int, default=1)

    analyze = sub.add_parser("analyze", help="Analyze a snapshot/evidence directory.")
    analyze.add_argument("--evidence", required=True)
    analyze.add_argument("--output", required=True)
    analyze.add_argument("--complaint-user", default="")
    analyze.add_argument("--complaint-host", default="")
    analyze.add_argument("--complaint-text", default="")
    analyze.add_argument("--known-patterns")
    analyze.add_argument("--feedback-store")
    analyze.add_argument("--markdown-output")

    incident = sub.add_parser("incident", help="Analyze a frontend complaint and write JSON plus one-page Markdown.")
    incident.add_argument("--evidence", required=True)
    incident.add_argument("--output", required=True)
    incident.add_argument("--markdown-output", required=True)
    incident.add_argument("--complaint-user", default="")
    incident.add_argument("--complaint-host", default="")
    incident.add_argument("--complaint-text", default="")
    incident.add_argument("--known-patterns")
    incident.add_argument("--feedback-store")

    feedback = sub.add_parser("feedback", help="Append operator feedback for future pattern learning.")
    feedback.add_argument("--store", required=True)
    feedback.add_argument("--signature", required=True)
    feedback.add_argument("--decision", required=True, choices=["intentional", "false-positive", "confirmed-root-cause", "deferred"])
    feedback.add_argument("--label", default="")
    feedback.add_argument("--form", default="")
    feedback.add_argument("--actor", default="operator")
    feedback.add_argument("--note", default="")

    args = parser.parse_args()
    if args.command == "record":
        for idx in range(args.samples):
            target = snapshot_dir(Path(args.source_evidence), Path(args.output_dir))
            print(f"Recorded snapshot {target}")
            if idx < args.samples - 1:
                time.sleep(args.interval_seconds)
        return 0
    if args.command == "analyze":
        payload = build_report(Path(args.evidence), Path(args.output), args.complaint_user, args.complaint_host, args.complaint_text, Path(args.known_patterns) if args.known_patterns else None, Path(args.feedback_store) if args.feedback_store else None, Path(args.markdown_output) if args.markdown_output else None)
        print(f"Wrote flight recorder report with {payload['rowCount']} rows to {args.output}")
        return 0
    if args.command == "incident":
        payload = build_report(Path(args.evidence), Path(args.output), args.complaint_user, args.complaint_host, args.complaint_text, Path(args.known_patterns) if args.known_patterns else None, Path(args.feedback_store) if args.feedback_store else None, Path(args.markdown_output))
        print(f"Wrote incident report with {payload['rowCount']} rows to {args.output} and {args.markdown_output}")
        return 0
    if args.command == "feedback":
        rows = write_feedback(Path(args.store), {
            "signature": args.signature,
            "decision": args.decision,
            "label": args.label,
            "form": args.form,
            "actor": args.actor,
            "note": args.note,
        })
        print(f"Wrote feedback entry {len(rows)} to {args.store}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
