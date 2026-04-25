import argparse
import json
from pathlib import Path


PLAYBOOKS = {
    "stale-statistics": ["Confirm statistics age and modification ratio", "Update targeted statistics in approved window", "Compare plan, reads, CPU, duration"],
    "blocking-chain": ["Identify root blocker", "Map blocker to AX process", "Reduce overlap or transaction duration", "Validate blocked duration trend"],
    "batch-collision-and-read-pressure": ["List overlapping jobs", "Correlate with waits and top queries", "Propose schedule/AOS changes", "Validate p95 runtime and SLA buffer"],
    "missing-composite-index-candidate": ["Validate missing-index signal", "Check existing AX indexes and write cost", "Prepare review candidate", "Measure reads and write overhead"],
    "data-growth": ["Confirm growth by date/company/module", "Check retention and audit requirements", "Prepare archive/cleanup assessment", "Validate runtime and maintenance duration"],
    "environment-drift": ["Compare prod/test SQL settings", "Compare indexes/statistics", "Compare data volume and batch setup", "Document reproducibility limits"],
    "deployment-regression": ["Identify change window", "Compare baseline and post-change evidence", "Isolate changed component", "Prepare rollback or fix proposal"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an action playbook for a finding type.")
    parser.add_argument("--playbook", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    steps = PLAYBOOKS.get(args.playbook)
    if not steps:
        raise SystemExit(f"Unknown playbook: {args.playbook}")
    payload = {"playbook": args.playbook, "steps": steps, "requiresApproval": True}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote playbook to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
