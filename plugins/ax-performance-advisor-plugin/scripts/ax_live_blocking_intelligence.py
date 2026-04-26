from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import infer_object_from_sql, load_evidence, owner_for_object, write_json


def _rows(evidence: str | Path) -> list[dict[str, Any]]:
    return load_evidence(evidence).tables.get("ax_live_blocking", [])


def _blocked(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if str(r.get("blocking_session_id") or "").lower() not in {"", "0", "n/a", "none"}]


def _object(row: dict[str, Any]) -> str:
    return infer_object_from_sql(str(row.get("statement_text") or ""))


def generate_ax_live_blocking_intelligence(evidence: str | Path) -> dict[str, Any]:
    rows = _rows(evidence)
    blocked = _blocked(rows)
    by_blocker: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_table = Counter()
    by_user = Counter()
    by_host = Counter()
    by_module = Counter()
    for row in blocked:
        blocker = str(row.get("blocking_session_id") or "")
        by_blocker[blocker].append(row)
        obj = _object(row) or "unknown"
        by_table[obj] += 1
        by_user[str(row.get("user_id") or "unknown")] += 1
        by_host[str(row.get("host_name") or "unknown")] += 1
        by_module[owner_for_object(obj)["module"]] += 1

    blocker_rows = []
    for blocker, items in by_blocker.items():
        max_wait = max(float(r.get("wait_time_ms") or 0) for r in items)
        tables = sorted({_object(r) or "unknown" for r in items})
        blocker_rows.append({
            "blockingSessionId": blocker,
            "blockedCount": len(items),
            "maxWaitMs": max_wait,
            "tables": tables[:8],
            "risk": "high" if len(items) > 1 or max_wait >= 120000 else "medium",
            "nextAction": "Map blocker to AX user/batch, capture input buffer/plan, then decide controlled stop/reschedule only with owner approval.",
        })

    critical_queries = []
    for row in blocked:
        sql = str(row.get("statement_text") or "")
        obj = _object(row) or "unknown"
        critical_queries.append({
            "sessionId": row.get("session_id"),
            "blockingSessionId": row.get("blocking_session_id"),
            "user": row.get("user_id"),
            "host": row.get("host_name"),
            "table": obj,
            "module": owner_for_object(obj)["module"],
            "elapsedMs": row.get("elapsed_time_ms"),
            "waitMs": row.get("wait_time_ms"),
            "queryClass": "update-contention" if sql.strip().upper().startswith("UPDATE") else "select-contention",
            "aiInterpretation": _interpret_query(sql, obj),
            "safeQuestion": f"Should AXPA prepare a blocking drilldown for session {row.get('session_id')} and blocker {row.get('blocking_session_id')}?",
        })

    return {
        "featureCount": 10,
        "sourceRows": len(rows),
        "blockedRows": len(blocked),
        "blockingChainRadar": sorted(blocker_rows, key=lambda r: (-r["blockedCount"], -r["maxWaitMs"])),
        "workerImpactMap": [{"user": user, "blockedSessions": count} for user, count in by_user.most_common()],
        "aosHostImpact": [{"host": host, "blockedSessions": count} for host, count in by_host.most_common()],
        "hotTableContention": [{"table": table, "blockedSessions": count, "module": owner_for_object(table)["module"]} for table, count in by_table.most_common()],
        "businessModuleImpact": [{"module": module, "blockedSessions": count} for module, count in by_module.most_common()],
        "criticalQueryClassifier": critical_queries,
        "safeActionQuestions": _safe_questions(blocked),
        "validationPlan": _validation_plan(blocked),
        "evidenceGaps": _evidence_gaps(rows, blocked),
        "executiveSummary": _executive_summary(blocked, by_table, by_module),
    }


def _interpret_query(sql: str, obj: str) -> str:
    token = obj.upper()
    action = "UPDATE" if sql.strip().upper().startswith("UPDATE") else "SELECT"
    if "GENERALJOURNALACCOUNTENTRY" in token:
        return f"{action} on finance ledger entry table; likely finance posting/close or ledger correction contention."
    if "INVENTSUM" in token or "INVENTDIM" in sql.upper():
        return f"{action} on inventory on-hand summary/dimensions; likely availability, reservation, MRP, or inventory recalculation pressure."
    return f"{action} on {obj or 'unknown object'}; needs AX owner/time-window validation."


def _safe_questions(blocked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question": "Soll ich die Blocker-Session mit DBCC INPUTBUFFER/DMV Detail pruefen?",
            "mode": "read-only",
            "why": "Identifies the exact blocking command before any operational decision.",
        },
        {
            "question": "Soll ich einen CAB-Vorschlag fuer kontrolliertes Entzerren/Stoppen vorbereiten?",
            "mode": "approval-required",
            "why": "Terminating AX workers can corrupt business process flow if done without owner approval.",
        },
        {
            "question": "Soll ich betroffene Tabellen gegen Index/Statistik/Plan-Evidence korrelieren?",
            "mode": "read-only",
            "why": "Links live blocking to sustainable remediation instead of one-time session kill.",
        },
    ] if blocked else []


def _validation_plan(blocked: list[dict[str, Any]]) -> list[str]:
    if not blocked:
        return ["Collect ax_live_blocking.csv during the incident window."]
    return [
        "Capture ax_live_blocking.csv during the same 09:00-style incident window.",
        "Capture blocking.csv, sql_wait_stats_delta.csv, plan_xml_inventory.csv and top query evidence at the same time.",
        "Confirm blocker owner before any stop/reschedule action.",
        "If schedule is changed, compare before/after blocked session count, max wait, elapsed time and affected table list.",
    ]


def _evidence_gaps(rows: list[dict[str, Any]], blocked: list[dict[str, Any]]) -> list[str]:
    gaps = []
    if not rows:
        gaps.append("No live AX blocking rows collected; run collect_sql_snapshot.ps1 during the issue window.")
    if blocked and not any(str(r.get("program_name") or "").lower().find("dynamics") >= 0 for r in blocked):
        gaps.append("Blocked rows exist but AX program names are missing; verify session attribution.")
    gaps.append("Exact X++ class/method still needs Trace Parser/DynamicsPerf or AX trace evidence.")
    return gaps


def _executive_summary(blocked: list[dict[str, Any]], by_table: Counter, by_module: Counter) -> dict[str, Any]:
    top_table = by_table.most_common(1)[0][0] if by_table else "none"
    top_module = by_module.most_common(1)[0][0] if by_module else "none"
    return {
        "message": f"{len(blocked)} live AX blocked worker/session rows detected; top impacted module {top_module}, top table {top_table}.",
        "risk": "high" if len(blocked) >= 2 else "medium" if blocked else "none",
        "managementAsk": "Approve read-only blocker drilldown and owner-led schedule/remediation review for recurring AX worker blocking.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate live AX blocking intelligence from DMV evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, generate_ax_live_blocking_intelligence(args.evidence))
    print(f"Wrote AX live blocking intelligence to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
