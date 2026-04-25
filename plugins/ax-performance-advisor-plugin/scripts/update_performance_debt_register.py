import argparse
import json
from pathlib import Path

from axpa_core import analyze_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or refresh a performance debt register.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    debt = [
        {
            "id": item["id"],
            "title": item["title"],
            "severity": item["severity"],
            "classification": item["classification"],
            "module": item["axContext"].get("module"),
            "owner": item["axContext"].get("technicalOwner"),
            "businessOwner": item["axContext"].get("businessOwner"),
            "recurrenceCount": item.get("performanceDebt", {}).get("recurrenceCount"),
            "ageDays": item.get("performanceDebt", {}).get("ageDays"),
            "nextDecision": item.get("performanceDebt", {}).get("nextDecision"),
            "status": item["status"],
        }
        for item in analyze_evidence(args.evidence)
        if item.get("performanceDebt", {}).get("isDebt")
    ]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(debt, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(debt)} debt items to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
