from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a lightweight Power BI template spec for AXPA CSV imports.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    template = {
        "name": "AXPA Executive Dashboard",
        "datasets": [{"name": "Findings", "source": "IT-TEST-ERP4CU-powerbi.csv"}],
        "pages": [
            {"name": "Executive Overview", "visuals": ["Health Score", "Top Risks", "Release Gate", "Cost of Delay"]},
            {"name": "SQL Performance", "visuals": ["Waits", "Top Queries", "Plan Repository"]},
            {"name": "AX Governance", "visuals": ["RACI", "Runbooks", "Admin Execution Gates"]},
            {"name": "AI/KI", "visuals": ["Hypothesis Ranking", "Counterfactuals", "Evidence Roadmap"]}
        ]
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote Power BI template spec to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
