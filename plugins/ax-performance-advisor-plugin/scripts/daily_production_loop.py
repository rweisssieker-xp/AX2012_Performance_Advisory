from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def generate_daily_production_loop(out_dir: str | Path, prefix: str) -> dict[str, Any]:
    out = Path(out_dir)
    operational = _load(out / f"{prefix}-operational-status.json")
    components = operational.get("components", {})
    payload = {
        "status": operational.get("status", "unknown"),
        "blockers": operational.get("blockers", []),
        "localAnalysisAllowed": True,
        "scheduler": components.get("scheduler", {"status": "missing", "summary": "no scheduler status"}),
        "push": components.get("push", {"status": "missing", "summary": "no push status"}),
        "dashboardHttpQa": components.get("dashboardHttpQa", {"status": "missing", "summary": "no dashboard QA"}),
        "dailyDelta": {"status": "trend-ready", "newFindings": [], "resolvedFindings": [], "worsenedFindings": [], "improvedFindings": []},
        "nextActions": [
            "Keep local analysis running even when push integrations are not configured.",
            "Install or repair scheduler when recurring daily runs are required.",
            "Configure push targets only after dry-run and duplicate protection are verified.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{prefix}-daily-production-loop.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# AXPA Daily Production Loop",
        "",
        f"Status: {payload['status']}",
        f"Blockers: {', '.join(payload['blockers']) if payload['blockers'] else 'none'}",
        "",
        "## Components",
    ]
    for name in ["scheduler", "push", "dashboardHttpQa"]:
        component = payload[name]
        lines.append(f"- {name}: {component.get('status')} - {component.get('summary')}")
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {action}" for action in payload["nextActions"]])
    (out / f"{prefix}-daily-production-loop.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA daily production loop summary.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    print(json.dumps(generate_daily_production_loop(args.out, args.prefix), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
