import argparse
import csv
import json
import hashlib
import sqlite3
from pathlib import Path

from axpa_core import analyze_evidence, batch_collision_summary, load_evidence, now_iso


def read_csv(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def signature(row: dict, fields: list[str]) -> str:
    raw = json.dumps({field: row.get(field, "") for field in fields}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def num(value: object) -> float:
    if value in (None, ""):
        return 0.0
    text = str(value).strip().replace(".", "").replace(",", ".") if "," in str(value) else str(value).strip()
    try:
        return float(text)
    except ValueError:
        return 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist AXPA run metrics into a SQLite trend store.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    evidence = load_evidence(args.evidence)
    findings = analyze_evidence(args.evidence)
    batch = batch_collision_summary(evidence)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, evidence TEXT, finding_count INTEGER, high_count INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS finding_history (run_id TEXT, id TEXT, severity TEXT, classification TEXT, module TEXT, title TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS batch_run_metrics (run_id TEXT PRIMARY KEY, task_count INTEGER, collision_count INTEGER, peak_concurrency INTEGER, peak_window TEXT, live_blocked_rows INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS batch_group_collisions (run_id TEXT, groups_name TEXT, collisions INTEGER, total_overlap_seconds INTEGER, max_overlap_seconds INTEGER, examples TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS plan_history (run_id TEXT, query_hash TEXT, plan_hash TEXT, operator_signature TEXT, duration_ms REAL, reads REAL, source TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS query_store_history (run_id TEXT, query_id TEXT, plan_id TEXT, duration_ms REAL, reads REAL, executions REAL)")
        conn.execute("CREATE TABLE IF NOT EXISTS index_history (run_id TEXT, table_name TEXT, index_name TEXT, fragmentation REAL, page_count REAL, signature TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS batch_config_history (run_id TEXT, batch_group TEXT, caption TEXT, class_number TEXT, aos TEXT, start_time TEXT, end_time TEXT, signature TEXT)")
        run_id = now_iso()
        conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?)", (run_id, args.evidence, len(findings), sum(1 for f in findings if f["severity"] in {"high", "critical"})))
        conn.executemany(
            "INSERT INTO finding_history VALUES (?, ?, ?, ?, ?, ?)",
            [(run_id, f["id"], f["severity"], f["classification"], f["axContext"].get("module", ""), f["title"]) for f in findings],
        )
        conn.execute(
            "INSERT INTO batch_run_metrics VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, batch["taskCount"], batch["collisionCount"], batch["peakConcurrency"], batch["peakWindow"], batch["liveBlockedRows"]),
        )
        conn.executemany(
            "INSERT INTO batch_group_collisions VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    item["groups"],
                    item["collisions"],
                    item["totalOverlapSeconds"],
                    item["maxOverlapSeconds"],
                    "; ".join(item.get("examples", [])),
                )
                for item in batch["groupCollisions"]
            ],
        )
        plan_rows = read_csv(Path(args.evidence) / "plan_xml_inventory.csv")
        conn.executemany(
            "INSERT INTO plan_history VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    row.get("query_hash", ""),
                    row.get("plan_hash", ""),
                    signature(row, ["query_plan", "statement_text", "plan_hash"]),
                    num(row.get("total_duration_ms") or row.get("duration_ms") or 0),
                    num(row.get("total_logical_reads") or row.get("logical_reads") or 0),
                    "plan_xml_inventory",
                )
                for row in plan_rows
            ],
        )
        qs_rows = read_csv(Path(args.evidence) / "query_store_runtime.csv")
        conn.executemany(
            "INSERT INTO query_store_history VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    row.get("query_id", ""),
                    row.get("plan_id", ""),
                    num(row.get("avg_duration_ms") or row.get("avg_duration") or 0),
                    num(row.get("avg_logical_io_reads") or row.get("avg_logical_reads") or 0),
                    num(row.get("count_executions") or row.get("execution_count") or 0),
                )
                for row in qs_rows
            ],
        )
        index_rows = read_csv(Path(args.evidence) / "index_fragmentation.csv")
        conn.executemany(
            "INSERT INTO index_history VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    row.get("table_name") or row.get("object_name") or row.get("table", ""),
                    row.get("index_name", ""),
                    num(row.get("avg_fragmentation_in_percent") or row.get("fragmentation") or 0),
                    num(row.get("page_count") or 0),
                    signature(row, ["table_name", "object_name", "index_name", "index_id"]),
                )
                for row in index_rows
            ],
        )
        batch_rows = read_csv(Path(args.evidence) / "batch_tasks.csv")
        conn.executemany(
            "INSERT INTO batch_config_history VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run_id,
                    row.get("batch_group", ""),
                    row.get("caption", ""),
                    row.get("class_number", ""),
                    row.get("aos", ""),
                    row.get("start_time", ""),
                    row.get("end_time", ""),
                    signature(row, ["batch_group", "caption", "class_number", "aos"]),
                )
                for row in batch_rows
            ],
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Updated trend store {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
