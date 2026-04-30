from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sqlite3
import urllib.request
import time
from datetime import datetime, timezone
from pathlib import Path

from axpa_core import analyze_evidence


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def dedupe_key(target: str, finding: dict) -> str:
    raw = json.dumps({"target": target, "id": finding.get("id"), "title": finding.get("title")}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def request_json(url: str, payload: object, headers: dict[str, str], method: str = "POST", retries: int = 2) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method=method, headers={"Content-Type": "application/json", **headers})
    last_error = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    parsed = {"body": body}
                return {"status": resp.status, "response": parsed, "attempts": attempt + 1}
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1 + attempt)
    raise RuntimeError(f"Push request failed after {retries + 1} attempts: {last_error}")


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS push_audit (dedupe_key TEXT PRIMARY KEY, target TEXT, finding_id TEXT, status TEXT, remote_id TEXT, pushed_at TEXT, response TEXT)")
    return conn


def already_pushed(conn: sqlite3.Connection, key: str) -> bool:
    return conn.execute("SELECT 1 FROM push_audit WHERE dedupe_key = ?", (key,)).fetchone() is not None


def record(conn: sqlite3.Connection, key: str, target: str, finding_id: str, status: str, remote_id: str, response: object) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO push_audit VALUES (?, ?, ?, ?, ?, ?, ?)",
        (key, target, finding_id, status, remote_id, now_iso(), json.dumps(response, ensure_ascii=False, default=str)),
    )
    conn.commit()


def push_teams(finding: dict, dry_run: bool) -> dict:
    url = os.environ.get("AXPA_TEAMS_WEBHOOK_URL", "")
    card = {"text": f"AXPA {finding['severity'].upper()}: {finding['title']}\n\n{finding.get('recommendation', {}).get('summary', '')}"}
    if dry_run:
        return {"status": "dry-run", "payload": card}
    if not url:
        raise RuntimeError("Missing AXPA_TEAMS_WEBHOOK_URL")
    return request_json(url, card, {})


def push_ado(finding: dict, dry_run: bool) -> dict:
    org = os.environ.get("AXPA_ADO_ORG") or os.environ.get("AZDO_ORG_URL", "")
    project = os.environ.get("AXPA_ADO_PROJECT") or os.environ.get("AZDO_PROJECT", "")
    token = os.environ.get("AXPA_ADO_TOKEN") or os.environ.get("AZDO_PAT", "")
    patch = [
        {"op": "add", "path": "/fields/System.Title", "value": finding["title"]},
        {"op": "add", "path": "/fields/System.Description", "value": finding.get("recommendation", {}).get("summary", "")},
        {"op": "add", "path": "/fields/System.Tags", "value": "AXPA"},
    ]
    if dry_run:
        return {"status": "dry-run", "payload": patch}
    if not org or not project or not token:
        raise RuntimeError("Missing AXPA_ADO_ORG/AXPA_ADO_PROJECT/AXPA_ADO_TOKEN")
    auth = base64.b64encode(f":{token}".encode()).decode()
    req = urllib.request.Request(f"{org.rstrip('/')}/{project}/_apis/wit/workitems/$Issue?api-version=7.1", data=json.dumps(patch).encode(), method="POST", headers={"Content-Type": "application/json-patch+json", "Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return {"status": resp.status, "response": json.loads(resp.read().decode())}


def push_jira(finding: dict, dry_run: bool) -> dict:
    base = os.environ.get("AXPA_JIRA_BASE_URL") or os.environ.get("JIRA_BASE_URL", "")
    project = os.environ.get("AXPA_JIRA_PROJECT") or os.environ.get("JIRA_PROJECT_KEY", "")
    email = os.environ.get("AXPA_JIRA_EMAIL") or os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("AXPA_JIRA_TOKEN") or os.environ.get("JIRA_API_TOKEN", "")
    payload = {"fields": {"project": {"key": project}, "summary": finding["title"], "description": finding.get("recommendation", {}).get("summary", ""), "issuetype": {"name": "Task"}, "labels": ["AXPA"]}}
    if dry_run:
        return {"status": "dry-run", "payload": payload}
    if not base or not project or not email or not token:
        raise RuntimeError("Missing AXPA_JIRA_BASE_URL/AXPA_JIRA_PROJECT/AXPA_JIRA_EMAIL/AXPA_JIRA_TOKEN")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    return request_json(f"{base.rstrip('/')}/rest/api/2/issue", payload, {"Authorization": f"Basic {auth}"})


def push_servicenow(finding: dict, dry_run: bool) -> dict:
    base = os.environ.get("AXPA_SN_INSTANCE_URL", "")
    token = os.environ.get("AXPA_SN_TOKEN", "")
    payload = {"short_description": f"AXPA: {finding['title']}", "description": finding.get("recommendation", {}).get("summary", ""), "category": "database"}
    if dry_run:
        return {"status": "dry-run", "payload": payload}
    if not base or not token:
        raise RuntimeError("Missing AXPA_SN_INSTANCE_URL/AXPA_SN_TOKEN")
    return request_json(f"{base.rstrip('/')}/api/now/table/incident", payload, {"Authorization": f"Bearer {token}"})


def push_powerbi(findings: list[dict], dry_run: bool) -> dict:
    endpoint = os.environ.get("AXPA_POWERBI_ENDPOINT") or os.environ.get("POWERBI_PUSH_ENDPOINT", "")
    rows = [{"id": f["id"], "title": f["title"], "severity": f["severity"], "playbook": f.get("recommendation", {}).get("playbook", "")} for f in findings]
    if dry_run:
        return {"status": "dry-run", "rows": len(rows)}
    if not endpoint:
        raise RuntimeError("Missing AXPA_POWERBI_ENDPOINT or POWERBI_PUSH_ENDPOINT")
    return request_json(endpoint, rows, {})


TARGETS = {"teams": push_teams, "ado": push_ado, "jira": push_jira, "servicenow": push_servicenow}


def main() -> int:
    parser = argparse.ArgumentParser(description="Push AXPA findings to external systems with dedupe and audit.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--targets", default="teams,ado,jira,servicenow,powerbi")
    parser.add_argument("--audit-db", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--replay-failed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    findings = sorted(analyze_evidence(args.evidence), key=lambda f: (f["severity"] in {"critical", "high"}, len(f.get("evidence", []))), reverse=True)[: args.limit]
    conn = init_db(Path(args.audit_db))
    results = []
    try:
        targets = [t.strip().lower() for t in args.targets.split(",") if t.strip()]
        if "powerbi" in targets:
            result = push_powerbi(findings, args.dry_run)
            record(conn, dedupe_key("powerbi", {"id": "dataset", "title": str(args.evidence)}), "powerbi", "dataset", str(result.get("status")), "", result)
            results.append({"target": "powerbi", "status": result.get("status")})
        for finding in findings:
            for target in targets:
                if target == "powerbi":
                    continue
                key = dedupe_key(target, finding)
                if already_pushed(conn, key):
                    results.append({"target": target, "findingId": finding["id"], "status": "duplicate-skipped"})
                    continue
                result = TARGETS[target](finding, args.dry_run)
                remote = str(result.get("response", {}).get("id") or result.get("response", {}).get("key") or "")
                record(conn, key, target, finding["id"], str(result.get("status")), remote, result)
                results.append({"target": target, "findingId": finding["id"], "status": result.get("status"), "remoteId": remote})
    finally:
        conn.close()
    print(json.dumps({"processedFindings": len(findings), "results": results}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
