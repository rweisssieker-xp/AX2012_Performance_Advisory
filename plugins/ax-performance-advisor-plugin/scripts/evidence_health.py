from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from axpa_core import load_evidence, write_json


KEY_SOURCES = [
    ("sql_top_queries.csv", "SQL top queries", "required"),
    ("sql_wait_stats.csv", "SQL wait stats", "required"),
    ("sql_wait_stats_delta.csv", "SQL wait delta", "recommended"),
    ("blocking.csv", "Blocking snapshot", "recommended"),
    ("deadlocks.csv", "Deadlock ring buffer", "recommended"),
    ("deadlock_processes.csv", "Parsed deadlock graph", "optional"),
    ("plan_xml_inventory.csv", "Plan XML inventory", "recommended"),
    ("plan_operators.csv", "Parsed plan operators", "recommended"),
    ("query_store_status.csv", "Query Store status", "recommended"),
    ("query_store_runtime.csv", "Query Store runtime", "recommended"),
    ("statistics_age.csv", "Statistics age", "required"),
    ("missing_indexes.csv", "Missing index candidates", "recommended"),
    ("batch_jobs.csv", "AX batch jobs", "recommended"),
    ("batch_tasks.csv", "AX batch tasks", "recommended"),
    ("user_sessions.csv", "AX user sessions", "recommended"),
    ("aos_counters.csv", "AOS counters", "recommended"),
    ("trace_parser.csv", "Trace Parser", "optional"),
    ("dynamicsperf.csv", "DynamicsPerf", "optional"),
]


def generate_evidence_health(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    loaded = load_evidence(root)
    rows = []
    for file_name, label, importance in KEY_SOURCES:
        path = root / file_name
        error = root / f"{file_name}.error.csv"
        if error.exists():
            status = "error"
        elif path.exists() and path.stat().st_size > 0:
            status = "present"
        elif path.exists():
            status = "empty"
        else:
            status = "missing"
        rows.append({
            "file": file_name,
            "label": label,
            "importance": importance,
            "status": status,
            "bytes": path.stat().st_size if path.exists() else 0,
            "errorFile": error.name if error.exists() else "",
        })
    present = sum(1 for row in rows if row["status"] == "present")
    errors = sum(1 for row in rows if row["status"] == "error")
    empty = sum(1 for row in rows if row["status"] == "empty")
    missing_required = sum(1 for row in rows if row["importance"] == "required" and row["status"] != "present")
    score = max(0, round(100 * present / len(rows) - errors * 8 - empty * 2 - missing_required * 15))
    return {
        "environment": loaded.metadata.get("environment") or root.name,
        "collectedAt": loaded.metadata.get("collectedAt", ""),
        "score": score,
        "summary": {"present": present, "error": errors, "empty": empty, "total": len(rows)},
        "sources": rows,
        "schemaDiscovery": loaded.tables.get("ax_schema_discovery", [])[:50],
        "sourceStatus": loaded.tables.get("source_status", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA evidence health summary.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, generate_evidence_health(args.evidence))
    print(f"Wrote evidence health to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
