import argparse
import csv
from pathlib import Path

from axpa_core import analyze_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Export findings as Jira/Azure DevOps compatible CSV backlog.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--system", choices=["jira", "azure-devops"], default="azure-devops")
    parser.add_argument("--minimum-severity", choices=["informational", "low", "medium", "high", "critical"], default="high")
    args = parser.parse_args()
    findings = analyze_evidence(args.evidence)
    min_rank = {"informational": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}[args.minimum_severity]
    rows = []
    for item in findings:
        if {"informational": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}.get(item["severity"], 0) < min_rank:
            continue
        rows.append({
            "Title": f"{item['id']} {item['title']}",
            "Work Item Type": "Issue" if args.system == "azure-devops" else "Task",
            "Description": item["recommendation"]["summary"],
            "Priority": item["severity"],
            "Tags": f"AXPA;{item['classification']};{item['axContext'].get('module', 'Unknown')}",
            "Assigned To": item["axContext"].get("technicalOwner", ""),
            "Acceptance Criteria": item["validation"].get("successMetric", ""),
        })
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["Title"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} ticket rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
