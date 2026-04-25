import argparse
import json
from pathlib import Path

from axpa_core import analyze_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SLA breach predictions from AXPA findings.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    predictions = [
        {
            "id": item["id"],
            "title": item["title"],
            "module": item["axContext"].get("module"),
            "slaBreachHorizonDays": item.get("prediction", {}).get("slaBreachHorizonDays"),
            "trendConfidence": item.get("prediction", {}).get("trendConfidence"),
            "capacitySignal": item.get("prediction", {}).get("capacitySignal"),
        }
        for item in analyze_evidence(args.evidence)
        if item.get("prediction", {}).get("slaBreachHorizonDays") is not None
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(predictions, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(predictions)} SLA predictions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
