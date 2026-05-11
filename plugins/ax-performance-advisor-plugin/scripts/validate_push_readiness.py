from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path


TARGET_ENV = {
    "teams": ["AXPA_TEAMS_WEBHOOK_URL"],
    "ado": ["AXPA_ADO_ORG", "AXPA_ADO_PROJECT", "AXPA_ADO_TOKEN"],
    "jira": ["AXPA_JIRA_BASE_URL", "AXPA_JIRA_PROJECT", "AXPA_JIRA_EMAIL", "AXPA_JIRA_TOKEN"],
    "servicenow": ["AXPA_SN_INSTANCE_URL", "AXPA_SN_TOKEN"],
    "powerbi": ["AXPA_POWERBI_ENDPOINT"],
}


def audit_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "records": 0, "duplicatesProtected": False, "statuses": {}}
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT status, COUNT(*) FROM push_audit GROUP BY status").fetchall()
        records = conn.execute("SELECT COUNT(*) FROM push_audit").fetchone()[0]
    finally:
        conn.close()
    return {"exists": True, "records": records, "duplicatesProtected": True, "statuses": {str(k): v for k, v in rows}}


def build(targets: list[str], audit_db: Path) -> dict:
    items = []
    for target in targets:
        names = TARGET_ENV.get(target, [])
        present = [name for name in names if os.environ.get(name)]
        missing = [name for name in names if not os.environ.get(name)]
        items.append({
            "target": target,
            "status": "ready" if names and not missing else "not-configured" if names else "unknown-target",
            "present": present,
            "missing": missing,
        })
    ready = sum(1 for item in items if item["status"] == "ready")
    audit = audit_stats(audit_db)
    return {
        "mode": "preflight",
        "targetCount": len(items),
        "readyTargets": ready,
        "status": "green" if ready == len(items) and audit["exists"] else "amber" if ready else "red",
        "targets": items,
        "auditDb": str(audit_db),
        "audit": audit,
        "nextAction": "Set missing environment variables and run push_integrations.py first with --dry-run, then without --dry-run after approval.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AXPA productive push configuration without sending data.")
    parser.add_argument("--targets", default="teams,ado,jira,servicenow,powerbi")
    parser.add_argument("--audit-db", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = build([x.strip().lower() for x in args.targets.split(",") if x.strip()], Path(args.audit_db))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] in {"green", "amber"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
