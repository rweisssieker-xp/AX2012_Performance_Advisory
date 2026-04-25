import argparse
import sqlite3
from pathlib import Path

from axpa_core import analyze_evidence, now_iso


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist AXPA run metrics into a SQLite trend store.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--db", required=True)
    args = parser.parse_args()
    findings = analyze_evidence(args.evidence)
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id TEXT PRIMARY KEY, evidence TEXT, finding_count INTEGER, high_count INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS finding_history (run_id TEXT, id TEXT, severity TEXT, classification TEXT, module TEXT, title TEXT)")
        run_id = now_iso()
        conn.execute("INSERT INTO runs VALUES (?, ?, ?, ?)", (run_id, args.evidence, len(findings), sum(1 for f in findings if f["severity"] in {"high", "critical"})))
        conn.executemany(
            "INSERT INTO finding_history VALUES (?, ?, ?, ?, ?, ?)",
            [(run_id, f["id"], f["severity"], f["classification"], f["axContext"].get("module", ""), f["title"]) for f in findings],
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Updated trend store {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
