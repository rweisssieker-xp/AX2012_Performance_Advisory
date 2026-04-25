import argparse
import base64
import csv
import json
import os
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Jira issues from AXPA ticket CSV.")
    parser.add_argument("--tickets", required=True)
    parser.add_argument("--base-url", default=os.environ.get("JIRA_BASE_URL", ""))
    parser.add_argument("--project-key", default=os.environ.get("JIRA_PROJECT_KEY", ""))
    parser.add_argument("--email", default=os.environ.get("JIRA_EMAIL", ""))
    parser.add_argument("--api-token", default=os.environ.get("JIRA_API_TOKEN", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and (not args.base_url or not args.project_key or not args.email or not args.api_token):
        raise SystemExit("Missing Jira credentials. Set JIRA_BASE_URL, JIRA_PROJECT_KEY, JIRA_EMAIL, JIRA_API_TOKEN or use --dry-run.")
    rows = list(csv.DictReader(Path(args.tickets).open("r", encoding="utf-8-sig")))
    created = []
    for row in rows:
        if args.dry_run:
            created.append({"title": row["Title"], "status": "dry-run"})
            continue
        payload = {"fields": {"project": {"key": args.project_key}, "summary": row["Title"], "description": row["Description"], "issuetype": {"name": "Task"}, "labels": ["AXPA"]}}
        token = base64.b64encode(f"{args.email}:{args.api_token}".encode()).decode()
        req = urllib.request.Request(f"{args.base_url.rstrip('/')}/rest/api/2/issue", data=json.dumps(payload).encode(), method="POST", headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            created.append(json.loads(resp.read().decode()))
    print(json.dumps({"processed": len(rows), "created": created}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
