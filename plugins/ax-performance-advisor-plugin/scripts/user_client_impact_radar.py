from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import _frontend_broad_inventory_signature, owner_for_object, write_json


TABLE_RE = re.compile(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Z0-9_.$\[\]]+)", re.IGNORECASE)
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
        return float(str(value).replace(",", "."))
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
    return seen[:8]


def _client_type_label(value: str) -> str:
    mapping = {"0": "unknown", "1": "batch/worker", "2": "web/service", "3": "rich-client"}
    return mapping.get(str(value).strip().lower(), str(value or "unknown"))


def _bucket(buckets: dict[str, dict[str, Any]], key: str, user: str, host: str) -> dict[str, Any]:
    item = buckets.setdefault(
        key,
        {
            "key": key,
            "user": user,
            "host": host,
            "sessions": set(),
            "activeSessionRows": 0,
            "liveRows": 0,
            "blockedRows": 0,
            "asBlockerRows": 0,
            "blockingSessionIds": Counter(),
            "blockedSessionIds": Counter(),
            "clientTypes": Counter(),
            "axStatuses": Counter(),
            "waitTypes": Counter(),
            "tables": Counter(),
            "queries": [],
            "logicalReads": 0.0,
            "elapsedMs": 0.0,
            "cpuMs": 0.0,
            "wideInventoryRows": 0,
        },
    )
    return item


def _finalize(item: dict[str, Any]) -> dict[str, Any]:
    blocked = int(item["blockedRows"])
    blocker = int(item["asBlockerRows"])
    reads = int(item["logicalReads"])
    elapsed = int(item["elapsedMs"])
    wide = int(item["wideInventoryRows"])
    session_count = len(item["sessions"])
    score = min(100, blocked * 25 + blocker * 20 + wide * 25 + int(reads / 1_000_000) + int(elapsed / 60_000) + int(item["liveRows"]) * 4 + min(session_count, 20))
    role = "active-session-context"
    if blocker and wide:
        role = "possible-blocker-machine-impact"
    elif blocker and blocked:
        role = "blocker-and-affected"
    elif blocker:
        role = "possible-blocker"
    elif wide:
        role = "machine-impact-suspect"
    top_tables = [{"table": k, "count": v, "module": owner_for_object(k)["module"]} for k, v in item["tables"].most_common(8)]
    next_questions = []
    if blocker:
        next_questions.append(f"Pruefen, warum User/Client {item['key']} als Blocker fuer andere Sessions auftritt.")
    if blocked:
        next_questions.append(f"Mit User/Client {item['key']} klaeren, welche AX-Aktion im Zeitfenster langsam war.")
    if wide:
        next_questions.append("Pruefen, ob eine breite Lagerbestand-/InventSum-Abfrage ueber viele Dimensionen gestartet wurde.")
    if not next_questions:
        next_questions.append("Nur beobachten; aktuell kein starker Blocking- oder Machine-Impact-Beleg.")
    return {
        "key": item["key"],
        "user": item["user"],
        "host": item["host"],
        "impactScore": score,
        "role": role,
        "sessionCount": session_count,
        "activeSessionRows": item["activeSessionRows"],
        "liveRows": item["liveRows"],
        "blockedRows": blocked,
        "asBlockerRows": blocker,
        "logicalReads": reads,
        "elapsedMs": elapsed,
        "cpuMs": int(item["cpuMs"]),
        "wideInventoryRows": wide,
        "clientTypes": [{"clientType": k, "count": v} for k, v in item["clientTypes"].most_common()],
        "axStatuses": [{"status": k, "count": v} for k, v in item["axStatuses"].most_common()],
        "waitTypes": [{"waitType": k, "count": v} for k, v in item["waitTypes"].most_common(6)],
        "topTables": top_tables,
        "blockingSessionIds": [{"sessionId": k, "count": v} for k, v in item["blockingSessionIds"].most_common(6)],
        "blockedSessionIds": [{"sessionId": k, "count": v} for k, v in item["blockedSessionIds"].most_common(6)],
        "sampleQueries": item["queries"][:4],
        "adminQuestions": next_questions,
    }


def generate_user_client_impact_radar(evidence: str | Path, output: str | Path | None = None) -> dict[str, Any]:
    root = Path(evidence)
    live_rows = _read_csv(root / "ax_live_blocking.csv")
    session_rows = _read_csv(root / "user_sessions.csv")
    by_user: dict[str, dict[str, Any]] = {}
    by_host: dict[str, dict[str, Any]] = {}
    by_pair: dict[str, dict[str, Any]] = {}
    blocker_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in live_rows:
        sid = _text(row, "session_id", "SessionId")
        if sid:
            blocker_sessions[sid].append(row)

    for row in session_rows:
        user = _text(row, "user_id", "UserId", "userid") or "unknown"
        host = _text(row, "client_computer", "host_name", "HostName") or "unknown"
        session_key = f"{user}@{host}"
        for key, buckets in [(user, by_user), (host, by_host), (session_key, by_pair)]:
            item = _bucket(buckets, key, user if buckets is not by_host else "", host if buckets is not by_user else "")
            item["activeSessionRows"] += 1
            item["sessions"].add(_text(row, "session_id", "SessionId") or f"session-row-{item['activeSessionRows']}")
            item["clientTypes"][_client_type_label(_text(row, "client_type", "ax_client_type", "AX-ClientType"))] += 1

    for row in live_rows:
        user = _text(row, "user_id", "UserId") or "unknown"
        host = _text(row, "host_name", "HostName", "client_computer") or "unknown"
        sid = _text(row, "session_id", "SessionId")
        blocker = _text(row, "blocking_session_id", "BlockingSessionId").lower()
        blocked = blocker not in BLOCKER_EMPTY
        statement = _text(row, "statement_text", "Query", "query_sql_text", "inputbuf")
        sig = _frontend_broad_inventory_signature(statement)
        tables = _tables(statement)
        query_summary = {
            "sessionId": sid,
            "blockingSessionId": _text(row, "blocking_session_id", "BlockingSessionId"),
            "database": _text(row, "database_name", "Database"),
            "command": _text(row, "command", "SQLServerStatus"),
            "logicalReads": int(_num(_text(row, "logical_reads", "reads"))),
            "elapsedMs": int(_num(_text(row, "elapsed_time_ms", "Elapsed_Time"))),
            "tables": tables,
            "statement": statement[:320],
        }
        targets = [
            _bucket(by_user, user, user, ""),
            _bucket(by_host, host, "", host),
            _bucket(by_pair, f"{user}@{host}", user, host),
        ]
        for item in targets:
            item["liveRows"] += 1
            if sid:
                item["sessions"].add(sid)
            if blocked:
                item["blockedRows"] += 1
                item["blockingSessionIds"][_text(row, "blocking_session_id", "BlockingSessionId")] += 1
            if sid and sid in blocker_sessions and any(_text(v, "blocking_session_id", "BlockingSessionId") == sid for v in live_rows):
                item["asBlockerRows"] += len(blocker_sessions[sid])
                item["blockedSessionIds"][sid] += len(blocker_sessions[sid])
            item["clientTypes"][_client_type_label(_text(row, "ax_client_type", "AX-ClientType"))] += 1
            item["axStatuses"][_text(row, "ax_status", "AX-Status") or "unknown"] += 1
            if _text(row, "wait_type"):
                item["waitTypes"][_text(row, "wait_type")] += 1
            for table in tables:
                item["tables"][table] += 1
            item["logicalReads"] += _num(_text(row, "logical_reads", "reads"))
            item["elapsedMs"] += _num(_text(row, "elapsed_time_ms", "Elapsed_Time"))
            item["cpuMs"] += _num(_text(row, "cpu_time_ms"))
            if sig.get("isInventoryWideQuery"):
                item["wideInventoryRows"] += 1
            if statement and len(item["queries"]) < 4:
                item["queries"].append(query_summary)

    users = sorted((_finalize(v) for v in by_user.values()), key=lambda x: x["impactScore"], reverse=True)
    hosts = sorted((_finalize(v) for v in by_host.values()), key=lambda x: x["impactScore"], reverse=True)
    pairs = sorted((_finalize(v) for v in by_pair.values()), key=lambda x: x["impactScore"], reverse=True)
    payload = {
        "mode": "internal-full-detail",
        "sourceFiles": {
            "axLiveBlocking": str(root / "ax_live_blocking.csv"),
            "userSessions": str(root / "user_sessions.csv"),
        },
        "sourceRows": {"axLiveBlocking": len(live_rows), "userSessions": len(session_rows)},
        "summary": {
            "users": len(users),
            "hosts": len(hosts),
            "userHostPairs": len(pairs),
            "blockedRows": sum(x["blockedRows"] for x in users),
            "wideInventoryRows": sum(x["wideInventoryRows"] for x in users),
            "topImpactScore": users[0]["impactScore"] if users else 0,
        },
        "topUsers": users[:30],
        "topClients": hosts[:30],
        "topUserClientPairs": pairs[:50],
        "clientTypeDistribution": [{"clientType": k, "count": v} for k, v in Counter(ct["clientType"] for x in users for ct in x["clientTypes"] for _ in range(ct["count"])).most_common()],
        "adminNextActions": [
            "Mit den Top-Usern/Clients aus der Liste den exakten AX-Dialog und Zeitpunkt klaeren.",
            "Bei machine-impact-suspect: Lagerbestand/InventSum-Abfragen nach Filterbreite und Dimensionen pruefen.",
            "Bei possible-blocker: blocking_session_id per read-only DMV/INPUTBUFFER Drilldown validieren, bevor operativ eingegriffen wird.",
            "Falls User/Host wiederholt auffaellig ist: Client/AOS-Zuordnung, Netz/Latenz und AX-Rolle fachlich pruefen.",
        ],
        "privacy": "internal-full-detail-no-masking",
        "writePolicy": "local-files-only-no-db-writes",
    }
    if output:
        write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate internal AX user/client impact radar from local evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    generate_user_client_impact_radar(args.evidence, args.output)
    print(f"Wrote user/client impact radar to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
