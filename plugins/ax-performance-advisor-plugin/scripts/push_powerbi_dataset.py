import argparse
import json
import os
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Push AXPA JSON rows to a Power BI streaming dataset endpoint.")
    parser.add_argument("--json", required=True)
    parser.add_argument("--endpoint", default=os.environ.get("POWERBI_PUSH_ENDPOINT", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = json.loads(Path(args.json).read_text(encoding="utf-8"))
    if args.dry_run:
        print(json.dumps({"rows": len(payload) if isinstance(payload, list) else 1, "status": "dry-run"}, indent=2))
        return 0
    if not args.endpoint:
        raise SystemExit("Missing POWERBI_PUSH_ENDPOINT or --endpoint.")
    req = urllib.request.Request(args.endpoint, data=json.dumps(payload).encode(), method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(resp.read().decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
