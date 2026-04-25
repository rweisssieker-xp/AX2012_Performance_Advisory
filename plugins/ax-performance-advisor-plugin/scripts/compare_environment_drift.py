import argparse
import json
from pathlib import Path

from axpa_core import analyze_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract environment drift findings.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    drift = [
        item for item in analyze_evidence(args.evidence)
        if item.get("environmentDrift", {}).get("productionOnly")
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(drift, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(drift)} drift findings to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
