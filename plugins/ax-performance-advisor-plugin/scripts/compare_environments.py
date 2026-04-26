from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, module_health_scores, write_json


def compare_environments(evidence_dirs: list[str | Path]) -> dict[str, Any]:
    rows = []
    for item in evidence_dirs:
        path = Path(item)
        if not path.exists():
            continue
        findings = analyze_evidence(path)
        high = sum(1 for f in findings if f["severity"] in {"critical", "high"})
        rows.append({
            "environment": path.name,
            "evidence": str(path),
            "findingCount": len(findings),
            "highCritical": high,
            "healthScores": module_health_scores(findings),
            "topPlaybooks": sorted(
                {f.get("recommendation", {}).get("playbook", "review") for f in findings}
            )[:10],
        })
    rows.sort(key=lambda r: (-r["highCritical"], -r["findingCount"], r["environment"]))
    return {"environmentCount": len(rows), "environments": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare AXPA evidence directories.")
    parser.add_argument("--evidence", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, compare_environments(args.evidence))
    print(f"Wrote environment comparison to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
