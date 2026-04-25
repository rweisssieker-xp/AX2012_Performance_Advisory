import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a Trace Parser CSV export into trace_parser.csv.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as src:
        reader = csv.DictReader(src)
        out_rows = []
        for row in reader:
            out_rows.append({
                "class_name": row.get("Class") or row.get("class_name") or row.get("ClassName") or "",
                "method_name": row.get("Method") or row.get("method_name") or row.get("MethodName") or "",
                "duration_ms": row.get("Duration") or row.get("duration_ms") or row.get("DurationMs") or "",
                "sql_text": row.get("SQL") or row.get("sql_text") or row.get("SqlText") or "",
            })
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=["class_name", "method_name", "duration_ms", "sql_text"])
        writer.writeheader()
        writer.writerows(out_rows)
    print(f"Wrote {len(out_rows)} normalized Trace Parser rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
