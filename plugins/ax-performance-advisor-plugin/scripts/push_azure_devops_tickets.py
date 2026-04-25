import argparse
import base64
import csv
import json
import os
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Azure DevOps work items from AXPA ticket CSV.")
    parser.add_argument("--tickets", required=True)
    parser.add_argument("--org-url", default=os.environ.get("AZDO_ORG_URL", ""))
    parser.add_argument("--project", default=os.environ.get("AZDO_PROJECT", ""))
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and (not args.org_url or not args.project or not args.pat):
        raise SystemExit("Missing Azure DevOps credentials. Set AZDO_ORG_URL, AZDO_PROJECT, AZDO_PAT or use --dry-run.")
    rows = list(csv.DictReader(Path(args.tickets).open("r", encoding="utf-8-sig")))
    created = []
    for row in rows:
        if args.dry_run:
            created.append({"title": row["Title"], "status": "dry-run"})
            continue
        url = f"{args.org_url.rstrip('/')}/{args.project}/_apis/wit/workitems/$Issue?api-version=7.1"
        patch = [
            {"op": "add", "path": "/fields/System.Title", "value": row["Title"]},
            {"op": "add", "path": "/fields/System.Description", "value": row["Description"]},
            {"op": "add", "path": "/fields/System.Tags", "value": row["Tags"]},
        ]
        token = base64.b64encode(f":{args.pat}".encode()).decode()
        req = urllib.request.Request(url, data=json.dumps(patch).encode(), method="POST", headers={"Content-Type": "application/json-patch+json", "Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            created.append(json.loads(resp.read().decode()))
    print(json.dumps({"processed": len(rows), "created": created}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
