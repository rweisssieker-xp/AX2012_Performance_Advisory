from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from axpa_core import analyze_evidence, write_json


def read_trace(path: Path) -> list[dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Map SQL/AX findings to Trace Parser/DynamicsPerf X++ evidence when present.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.evidence)
    findings = analyze_evidence(root)
    trace_rows = read_trace(root / "trace_parser.csv") + read_trace(root / "dynamicsperf_trace.csv")
    mappings = []
    for finding in findings:
        objects = finding.get("axContext", {}).get("tables", []) + finding.get("sqlContext", {}).get("objects", [])
        matches = []
        for row in trace_rows:
            text = json.dumps(row, ensure_ascii=False).lower()
            if any(obj.lower().split(".")[-1] in text for obj in objects):
                matches.append(row)
        mappings.append({
            "findingId": finding["id"],
            "title": finding["title"],
            "status": "mapped" if matches else "requires-trace-evidence",
            "matches": matches[:10],
            "requiredEvidence": "" if matches else "Provide normalized trace_parser.csv or dynamicsperf_trace.csv with class/method/sql_text.",
        })
    write_json(args.output, {"traceRows": len(trace_rows), "mapped": sum(1 for m in mappings if m["status"] == "mapped"), "mappings": mappings})
    print(f"Wrote X++ attribution report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
