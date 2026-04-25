from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


SEVERITY_RANK = {"informational": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def load_policy(path: str | Path | None = None) -> dict[str, Any]:
    policy_path = Path(path) if path else Path(__file__).resolve().parents[1] / "rules" / "execution_policy.json"
    return json.loads(policy_path.read_text(encoding="utf-8"))


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text)[:90]


def action_type(finding: dict[str, Any]) -> str:
    playbook = finding.get("recommendation", {}).get("playbook", "")
    if playbook == "stale-statistics":
        return "update-statistics-review"
    if "index" in playbook:
        return "index-maintenance-review"
    if "batch" in playbook:
        return "batch-schedule-review"
    if playbook in {"deployment-regression", "parameter-sensitive-plan"}:
        return "query-store-review"
    return "post-change-validation"


def confirmation_token(finding_id: str, environment: str, action: str) -> str:
    raw = f"{finding_id}|{environment.upper()}|{action}|AXPA".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:12].upper()


def _primary_object(finding: dict[str, Any]) -> str:
    objects = finding.get("sqlContext", {}).get("objects", []) or finding.get("axContext", {}).get("tables", [])
    return objects[0] if objects else ""


def preview_script(finding: dict[str, Any], environment: str, action: str) -> str:
    obj = _primary_object(finding)
    token = confirmation_token(finding["id"], environment, action)
    header = f"""/*
AXPA Admin Execution Preview
Finding: {finding['id']} - {finding['title']}
Environment: {environment}
ActionType: {action}
ConfirmationToken: {token}
Mode: PREVIEW. Review, approve, and adapt before execution.
*/
"""
    if action == "update-statistics-review" and obj:
        return header + f"""
-- Proposed TEST/PREPROD action. Do not run in PROD without CAB approval.
-- Review sample/fullscan choice for table size and maintenance window.
UPDATE STATISTICS {obj};
-- Validation:
-- Re-run AXPA evidence collection and compare logical reads, duration, waits, and plan stability.
"""
    if action == "index-maintenance-review" and obj:
        return header + f"""
-- Proposed index-maintenance review only. Missing-index DMV output is not a direct create instruction.
-- Inspect existing AX indexes, write overhead, DataAreaId/Partition/RecId patterns, and table volume.
SELECT * FROM sys.indexes WHERE object_id = OBJECT_ID(N'{obj}');
-- Create/rebuild scripts must be authored by DBA/AX owner after TEST validation.
"""
    if action == "query-store-review":
        return header + """
-- Query Store review. Do not force a plan without before/after evidence and rollback note.
SELECT TOP (50) * FROM sys.query_store_query ORDER BY query_id DESC;
-- Review query_id/runtime_stats for the finding query hash/plan hash.
"""
    if action == "batch-schedule-review":
        return header + """
-- AX batch schedule review. Use AX client/admin tooling or approved deployment process.
-- Validate collision reduction with post-change AXPA evidence.
"""
    return header + """
-- Post-change validation action.
-- Re-run collectors for a comparable business window and execute compare_baseline.py.
"""


def build_execution_plan(
    evidence: str | Path,
    output_dir: str | Path,
    environment: str = "TEST",
    minimum_severity: str = "high",
    approval_reference: str = "",
    confirm_token: str = "",
) -> dict[str, Any]:
    policy = load_policy()
    env = environment.upper()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scripts_dir = out / "preview-scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = out / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    findings = [f for f in analyze_evidence(evidence) if SEVERITY_RANK.get(f["severity"], 0) >= SEVERITY_RANK[minimum_severity]]
    actions = []
    for finding in findings:
        act = action_type(finding)
        token = confirmation_token(finding["id"], env, act)
        approved = bool(approval_reference)
        env_allowed = env in policy["allowedEnvironments"]
        token_ok = confirm_token == token
        executable = env_allowed and approved and token_ok and act in policy["allowedActionTypes"]
        script_path = scripts_dir / f"{finding['id']}-{safe_name(act)}.sql"
        script_path.write_text(preview_script(finding, env, act), encoding="utf-8")
        actions.append(
            {
                "findingId": finding["id"],
                "title": finding["title"],
                "severity": finding["severity"],
                "environment": env,
                "actionType": act,
                "status": "executable-after-final-review" if executable else "preview-only",
                "script": str(script_path),
                "confirmationToken": token,
                "approvalReference": approval_reference,
                "gates": {
                    "environmentAllowed": env_allowed,
                    "approvalReferencePresent": approved,
                    "confirmationTokenMatched": token_ok,
                    "actionTypeAllowed": act in policy["allowedActionTypes"],
                    "prodBlockedByDefault": env == "PROD",
                },
                "rollback": finding.get("validation", {}).get("rollback", "Rollback must be documented before implementation."),
                "validation": finding.get("validation", {}).get("successMetric", "Compare before/after evidence."),
            }
        )
    result = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": policy["defaultMode"],
        "environment": env,
        "actionCount": len(actions),
        "executableCount": sum(1 for a in actions if a["status"] != "preview-only"),
        "policy": policy,
        "actions": actions,
    }
    write_json(out / "admin-execution-plan.json", result)
    write_json(
        audit_dir / "admin-execution-audit.json",
        {
            "generatedAt": result["generatedAt"],
            "environment": env,
            "approvalReference": approval_reference,
            "actionCount": len(actions),
            "executableCount": result["executableCount"],
            "note": "Preview generation only; execution requires separate admin review and database/tool execution.",
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate guarded admin execution previews for AXPA findings.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--environment", default="TEST")
    parser.add_argument("--minimum-severity", default="high", choices=["informational", "low", "medium", "high", "critical"])
    parser.add_argument("--approval-reference", default="")
    parser.add_argument("--confirm-token", default="")
    args = parser.parse_args()
    result = build_execution_plan(
        args.evidence,
        args.output_dir,
        args.environment,
        args.minimum_severity,
        args.approval_reference,
        args.confirm_token,
    )
    print(f"Wrote {result['actionCount']} admin execution previews to {args.output_dir}")
    print(f"Executable after gates: {result['executableCount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
