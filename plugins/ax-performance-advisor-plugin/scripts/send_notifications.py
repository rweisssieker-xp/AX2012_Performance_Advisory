from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib import request

from axpa_core import write_json


def post_json(url: str, payload: object) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=30) as resp:
        return resp.status


def main() -> int:
    parser = argparse.ArgumentParser(description="Send AXPA notification payloads. Defaults to dry-run.")
    parser.add_argument("--payload-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    root = Path(args.payload_dir)
    teams = json.loads((root / "teams-card.json").read_text(encoding="utf-8")) if (root / "teams-card.json").exists() else None
    result = {"mode": "send" if args.send else "dry-run", "attempts": []}
    if teams:
        url = os.getenv("AXPA_TEAMS_WEBHOOK_URL", "")
        if args.send and url:
            status = post_json(url, teams)
            result["attempts"].append({"system": "teams", "status": status})
        else:
            result["attempts"].append({"system": "teams", "status": "not-sent", "reason": "dry-run or missing AXPA_TEAMS_WEBHOOK_URL"})
    write_json(args.output, result)
    print(f"Wrote notification result to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
