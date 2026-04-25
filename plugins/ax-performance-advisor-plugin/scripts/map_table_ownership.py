import argparse
import csv
import json
from pathlib import Path

from axpa_core import owner_for_object, read_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Map AX SQL object names to module and owner metadata.")
    parser.add_argument("--objects", nargs="+", required=True)
    parser.add_argument("--ownership-csv")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = read_csv(Path(args.ownership_csv)) if args.ownership_csv else []
    mapped = [{"object": name, **owner_for_object(name, rows)} for name in args.objects]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(mapped, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(mapped)} ownership mappings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
