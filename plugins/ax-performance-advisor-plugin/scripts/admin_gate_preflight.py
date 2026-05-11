from __future__ import annotations

import argparse
import json
from pathlib import Path

from admin_execution import build_execution_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight AXPA admin execution gates and write a Go/No-Go summary.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--environment", default="TEST")
    parser.add_argument("--minimum-severity", default="high")
    parser.add_argument("--approval-reference", default="")
    parser.add_argument("--confirm-token", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    plan = build_execution_plan(
        args.evidence,
        args.output_dir,
        args.environment,
        args.minimum_severity,
        args.approval_reference,
        args.confirm_token,
    )
    blocked = [a for a in plan["actions"] if a["status"] == "preview-only"]
    executable = [a for a in plan["actions"] if a["status"] != "preview-only"]
    summary = {
        "mode": "admin-gate-preflight",
        "environment": args.environment,
        "actionCount": plan["actionCount"],
        "executableCount": len(executable),
        "blockedCount": len(blocked),
        "status": "green" if executable and not blocked else "amber" if plan["actionCount"] else "green",
        "goNoGo": "GO for gated TEST execution" if executable and not blocked else "NO-GO until approval reference and confirmation token match",
        "firstRequiredToken": blocked[0]["confirmationToken"] if blocked else "",
        "blockedReasons": [
            {"findingId": a["findingId"], "gates": {k: v for k, v in a["gates"].items() if not v}}
            for a in blocked[:20]
        ],
    }
    output = Path(args.output) if args.output else Path(args.output_dir) / "admin-gate-preflight.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
