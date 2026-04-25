import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize DynamicsPerf CSV exports into dynamicsperf.csv.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        rows = []
        for row in reader:
            rows.append({
                "capture_time": row.get("capture_time") or row.get("CaptureTime") or row.get("StartTime") or "",
                "object_name": row.get("object_name") or row.get("ObjectName") or row.get("TableName") or "",
                "query_hash": row.get("query_hash") or row.get("QueryHash") or "",
                "duration_ms": row.get("duration_ms") or row.get("DurationMs") or row.get("Duration") or "",
                "logical_reads": row.get("logical_reads") or row.get("LogicalReads") or row.get("Reads") or "",
                "cpu_ms": row.get("cpu_ms") or row.get("CpuMs") or row.get("CPU") or "",
            })
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=["capture_time", "object_name", "query_hash", "duration_ms", "logical_reads", "cpu_ms"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} normalized DynamicsPerf rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
