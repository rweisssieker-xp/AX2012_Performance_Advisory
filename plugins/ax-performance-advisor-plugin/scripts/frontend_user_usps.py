from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import _frontend_broad_inventory_signature, owner_for_object, write_json
from user_client_impact_radar import generate_user_client_impact_radar


TABLE_RE = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Z0-9_.$\[\]]+)", re.IGNORECASE)
FILTER_RE = re.compile(r"\b(DATAAREAID|PARTITION|ITEMID|INVENTSITEID|INVENTLOCATIONID|CONFIGID|DATEPHYSICAL|ACCOUNTNUM|RECID)\b", re.IGNORECASE)
BLOCKER_EMPTY = {"", "0", "n/a", "none", "null"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _num(value: Any, default: float = 0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return default


def _text(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _tables(statement: str) -> list[str]:
    seen: list[str] = []
    for raw in TABLE_RE.findall(statement or ""):
        table = raw.strip("[]").split(".")[-1].upper()
        if table and table not in seen:
            seen.append(table)
    return seen[:10]


def _filters(statement: str) -> list[str]:
    seen: list[str] = []
    for raw in FILTER_RE.findall(statement or ""):
        key = raw.upper()
        if key not in seen:
            seen.append(key)
    return seen


def _likely_forms(tables: list[str], statement: str) -> list[str]:
    upper = (statement or "").upper()
    forms: list[str] = []
    if "INVENTSUM" in tables or "INVENTDIM" in tables:
        forms.extend(["InventOnHand", "InventTable", "InventDim"])
    if "GENERALJOURNALACCOUNTENTRY" in tables or "GENERALJOURNALENTRY" in tables:
        forms.extend(["LedgerJournalTable", "GeneralJournalEntry", "LedgerTransVoucher"])
    if "CUSTTRANS" in tables:
        forms.extend(["CustTrans", "CustTable"])
    if "VENDTRANS" in tables:
        forms.extend(["VendTrans", "VendTable"])
    if "SALESLINE" in tables or "SALESTABLE" in tables:
        forms.extend(["SalesTable", "SalesLine"])
    if "PURCHLINE" in tables or "PURCHTABLE" in tables:
        forms.extend(["PurchTable", "PurchLine"])
    if "SUM(" in upper and ("INVENTSUM" in tables or "INVENTDIM" in tables):
        forms.insert(0, "InventOnHand")
    return list(dict.fromkeys(forms or ["unknown-form"]))


def _business_process(tables: list[str]) -> str:
    modules = [owner_for_object(table)["module"] for table in tables]
    if not modules:
        return "Unknown"
    return Counter(modules).most_common(1)[0][0]


def _statement_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source, filename in [("live-blocking", "ax_live_blocking.csv"), ("top-query", "sql_top_queries.csv")]:
        for row in _read_csv(root / filename):
            statement = _text(row, "statement_text", "Query", "query_sql_text", "inputbuf")
            if not statement:
                continue
            tables = _tables(statement)
            filters = _filters(statement)
            wide = _frontend_broad_inventory_signature(statement)
            reads = _num(_text(row, "logical_reads", "total_logical_reads", "avg_logical_reads", "reads"))
            elapsed = _num(_text(row, "elapsed_time_ms", "total_duration_ms", "avg_duration_ms", "Elapsed_Time"))
            rows.append(
                {
                    "source": source,
                    "user": _text(row, "user_id", "UserId") or "unknown",
                    "host": _text(row, "host_name", "HostName", "client_computer") or "unknown",
                    "sessionId": _text(row, "session_id", "SessionId"),
                    "blockingSessionId": _text(row, "blocking_session_id", "BlockingSessionId"),
                    "waitType": _text(row, "wait_type"),
                    "logicalReads": int(reads),
                    "elapsedMs": int(elapsed),
                    "cpuMs": int(_num(_text(row, "cpu_time_ms", "total_cpu_ms"))),
                    "executionCount": int(_num(_text(row, "execution_count"), 1)),
                    "queryHash": _text(row, "query_hash") or _text(row, "session_id", "SessionId") or "unknown",
                    "statement": statement,
                    "tables": tables,
                    "filters": filters,
                    "businessProcess": _business_process(tables),
                    "wideInventory": bool(wide.get("isInventoryWideQuery")),
                    "dimensionCount": int(wide.get("dimensionCount", 0)),
                    "orPredicateCount": int(wide.get("orPredicateCount", 0)),
                    "checkTime": _text(row, "check_time", "last_execution_time", "start_time"),
                }
            )
    return rows


def _top_counter(rows: list[dict[str, Any]], field: str, limit: int = 10) -> list[dict[str, Any]]:
    counter = Counter(str(row.get(field) or "unknown") for row in rows)
    return [{"name": name, "value": value} for name, value in counter.most_common(limit)]


def _stress_tables(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        for table in row["tables"]:
            bucket = buckets.setdefault(table, {"table": table, "reads": 0, "elapsedMs": 0, "hits": 0, "blockedHits": 0, "module": owner_for_object(table)["module"]})
            bucket["reads"] += row["logicalReads"]
            bucket["elapsedMs"] += row["elapsedMs"]
            bucket["hits"] += 1
            if str(row.get("blockingSessionId") or "").lower() not in BLOCKER_EMPTY:
                bucket["blockedHits"] += 1
    for bucket in buckets.values():
        bucket["stressScore"] = min(100, bucket["hits"] * 8 + bucket["blockedHits"] * 20 + int(bucket["reads"] / 5_000_000) + int(bucket["elapsedMs"] / 60_000))
        bucket["recommendation"] = "Prefer archive/data lifecycle review before more tuning." if bucket["reads"] > 100_000_000 else "Review query, index and statistics evidence in TEST."
    return sorted(buckets.values(), key=lambda x: x["stressScore"], reverse=True)[:20]


def _guardrails(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules = []
    if any(row["wideInventory"] for row in rows):
        rules.append({"rule": "Inventory on-hand queries require Site/Warehouse or Item filter for business hours.", "why": "Broad InventSum/InventDim aggregations can create machine-wide read pressure.", "owner": "Inventory"})
    if any(str(row.get("blockingSessionId") or "").lower() not in BLOCKER_EMPTY for row in rows):
        rules.append({"rule": "Do not run finance postings or imports in the same window as active blocking chains.", "why": "Blocking rows show live contention and user impact.", "owner": "AX Operations"})
    if not rules:
        rules.append({"rule": "Keep read-only monitoring active and review frontend complaints with lightweight flight recorder.", "why": "No strong misuse signal in current snapshot.", "owner": "AX Operations"})
    rules.append({"rule": "All recommendations remain local-file advisory until TEST/CAB approval.", "why": "Remote AX/SQL systems must stay read-only from this plugin.", "owner": "IT Governance"})
    return rules


def generate_frontend_user_usps(evidence: str | Path, output: str | Path | None = None) -> dict[str, Any]:
    root = Path(evidence)
    rows = _statement_rows(root)
    radar = generate_user_client_impact_radar(root)
    top_users = radar.get("topUsers", [])
    top_clients = radar.get("topClients", [])
    wide_rows = [row for row in rows if row["wideInventory"]]
    blocked_rows = [row for row in rows if str(row.get("blockingSessionId") or "").lower() not in BLOCKER_EMPTY]
    stress = _stress_tables(rows)
    process_counts = Counter(row["businessProcess"] for row in rows)
    host_counts = Counter(row["host"] for row in rows)
    hour_counts = Counter(str(row.get("checkTime", ""))[11:13] or "unknown" for row in rows)
    top_blast = []
    for row in sorted(wide_rows, key=lambda x: (x["logicalReads"], x["elapsedMs"]), reverse=True)[:20]:
        top_blast.append(
            {
                "user": row["user"],
                "host": row["host"],
                "sessionId": row["sessionId"],
                "affectedUsers": max(1, len(blocked_rows) + len({r["user"] for r in rows if r["host"] == row["host"]}) - 1),
                "tables": row["tables"],
                "logicalReads": row["logicalReads"],
                "elapsedMs": row["elapsedMs"],
                "why": "Broad inventory aggregation over InventSum/InventDim can monopolize reads and slow the whole AX stack.",
                "containment": "Ask user to narrow filters or move report to batch; validate with live blocking and Query Store evidence.",
            }
        )
    form_items = [
        {
            "queryHash": row["queryHash"],
            "tables": row["tables"],
            "likelyForms": _likely_forms(row["tables"], row["statement"]),
            "confidence": "high" if row["wideInventory"] or row["tables"] else "low",
            "businessProcess": row["businessProcess"],
            "evidence": f"{row['source']} user={row['user']} host={row['host']} reads={row['logicalReads']}",
        }
        for row in rows[:50]
    ]
    misuse = []
    if wide_rows:
        misuse.append({"pattern": "broad-inventory-query", "count": len(wide_rows), "risk": "high", "coaching": "Use Item, Site, Warehouse and relevant dimensions before calculating on-hand inventory."})
    unfiltered = [row for row in rows if len(row["filters"]) < 2 and row["logicalReads"] > 1_000_000]
    if unfiltered:
        misuse.append({"pattern": "low-filter-quality-high-read-query", "count": len(unfiltered), "risk": "medium", "coaching": "Add company/business filters and avoid all-record lookups during core hours."})
    if not misuse:
        misuse.append({"pattern": "no-strong-misuse-detected", "count": 0, "risk": "low", "coaching": "Keep collecting lightweight snapshots during complaints."})
    read_amp = []
    for row in sorted(rows, key=lambda x: x["logicalReads"] / max(1, x["executionCount"]), reverse=True)[:20]:
        read_amp.append({"queryHash": row["queryHash"], "readsPerExecution": int(row["logicalReads"] / max(1, row["executionCount"])), "executionCount": row["executionCount"], "tables": row["tables"], "assessment": "high amplification" if row["logicalReads"] > 10_000_000 else "watch"})
    filter_quality = []
    for row in rows[:50]:
        required = {"DATAAREAID", "PARTITION"}
        if "INVENTSUM" in row["tables"] or "INVENTDIM" in row["tables"]:
            required.update({"ITEMID", "INVENTSITEID", "INVENTLOCATIONID"})
        missing = sorted(required - set(row["filters"]))
        filter_quality.append({"queryHash": row["queryHash"], "tables": row["tables"], "presentFilters": row["filters"], "missingRecommendedFilters": missing, "quality": "good" if not missing else "weak"})
    do_not_run = []
    if wide_rows:
        do_not_run.append({"left": "Inventory on-hand full dimension query", "right": "MRP / Inventory close / AIF import", "reason": "Read pressure plus batch write pressure increases system-wide slowdowns.", "recommendation": "Move broad report outside batch peak or enforce filters."})
    if blocked_rows:
        do_not_run.append({"left": "Finance posting/update", "right": "long SELECT/reporting workload", "reason": "Live blocking evidence shows user-facing wait chains.", "recommendation": "Separate update-heavy and reporting-heavy windows."})
    evidence_first = []
    for idx, row in enumerate(sorted(rows, key=lambda x: x["logicalReads"] + x["elapsedMs"], reverse=True)[:8], start=1):
        evidence_first.append({"step": idx, "hypothesis": f"{row['businessProcess']} query pressure from {', '.join(row['tables'][:3]) or 'unknown table'}", "proveFirst": "Collect live blocking + Query Store runtime for same timestamp.", "then": "Ask user/client what AX form/action was open and compare filter quality.", "confidence": "high" if row["wideInventory"] else "medium"})
    lost_minutes = sum(max(row["elapsedMs"], 0) for row in rows) / 60000 + len(blocked_rows) * 5
    cost_low = int(lost_minutes * 0.8)
    cost_high = int(lost_minutes * 2.5 + len(top_users) * 20)
    features = {
        "axUserFrictionIndex": {"topUsers": [{"user": x.get("user"), "host": x.get("host"), "score": x.get("impactScore"), "role": x.get("role"), "adminQuestions": x.get("adminQuestions", [])} for x in top_users[:20]], "metric": "blocking + reads + elapsed time + wide inventory signals"},
        "frontendBlastRadiusRadar": {"blastRadiusItems": top_blast, "affectedHostCount": len({x["host"] for x in top_blast}), "summary": "Shows who triggered machine-wide read pressure and who may be affected."},
        "axFormToSqlAttribution": {"items": form_items, "method": "table signatures + statement intent + user/session/host evidence; no Trace Parser required"},
        "misusePatternDetection": {"patterns": misuse},
        "clientHostReputationScore": {"topClients": [{"host": x.get("host"), "score": x.get("impactScore"), "role": x.get("role"), "blockedRows": x.get("blockedRows"), "wideInventoryRows": x.get("wideInventoryRows")} for x in top_clients[:20]]},
        "businessProcessHeatmap": {"processes": [{"process": k, "count": v} for k, v in process_counts.most_common()], "topRiskProcess": process_counts.most_common(1)[0][0] if process_counts else "Unknown"},
        "axPerformanceGuardrails": {"rules": _guardrails(rows)},
        "smartUserCoachingPack": {"coachingItems": [{"targetUser": x.get("user"), "targetHost": x.get("host"), "message": "; ".join(x.get("adminQuestions", [])[:2]) or "Review AX action and filters during complaint window."} for x in top_users[:20]]},
        "aosDrainRecommendation": {"hosts": [{"host": k, "queryRows": v, "recommendation": "Candidate for AOS drain/isolation review during peak." if v >= 2 else "Monitor only."} for k, v in host_counts.most_common(20)]},
        "criticalTableStressIndex": {"tables": stress},
        "readAmplificationDetector": {"items": read_amp},
        "filterQualityAdvisor": {"items": filter_quality, "weakCount": sum(1 for x in filter_quality if x["quality"] == "weak")},
        "doNotRunTogetherMatrix": {"rules": do_not_run or [{"left": "No strong current conflict", "right": "Keep monitoring", "reason": "Current snapshot lacks conflicting pressure signals.", "recommendation": "Build matrix from next complaint windows."}]},
        "incidentFingerprintLibrary": {"fingerprints": [{"name": "Inventory Availability Storm", "active": bool(wide_rows), "signature": "InventSum + InventDim + SUM + multiple dimensions"}, {"name": "Blocking User Chain", "active": bool(blocked_rows), "signature": "blocking_session_id present in AX live blocking"}]},
        "aiEvidenceFirstTroubleshooter": {"steps": evidence_first},
        "axSlowMorningDetector": {"hourBuckets": [{"hour": k, "events": v} for k, v in sorted(hour_counts.items())], "morningRisk": sum(v for k, v in hour_counts.items() if k in {"07", "08", "09"})},
        "sqlToAxTableSemanticExplainer": {"tables": [{"table": x["table"], "module": x["module"], "plainLanguage": f"{x['table']} belongs to {x['module']} and should be evaluated with business owner context.", "risk": x["stressScore"]} for x in stress]},
        "changeFreezeRiskAdvisor": {"recommendations": [{"finding": "frontend/user performance action", "freezeRisk": "high" if process_counts.get("Finance", 0) else "medium", "guidance": "Avoid PROD changes during month-end, inventory count, audit or production peak; validate in TEST first."}]},
        "executiveBusinessLossEstimator": {"lostMinutesEstimate": round(lost_minutes, 1), "estimatedCostLowEur": cost_low, "estimatedCostHighEur": max(1, cost_high), "assumption": "Local estimate based on elapsed query time, blocking rows and affected user/client signals."},
        "axModernizationPressureIndex": {"score": min(100, len(stress) * 4 + len(wide_rows) * 15 + len(blocked_rows) * 10), "decision": "tune-and-coach-first" if len(wide_rows) + len(blocked_rows) < 5 else "archive-modernize-and-tune", "signals": ["wide inventory query"] if wide_rows else ["insufficient frontend pressure evidence"]},
    }
    payload = {
        "featureCount": len(features),
        "features": features,
        "sourceRows": {"statements": len(rows), "wideInventory": len(wide_rows), "blocked": len(blocked_rows)},
        "writePolicy": "local-files-only-no-db-writes",
        "mode": "internal-full-detail",
    }
    if output:
        write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 20 concrete AX frontend/user USP analyses from local evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate_frontend_user_usps(args.evidence, args.output)
    print(f"Wrote frontend/user USP pack to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
