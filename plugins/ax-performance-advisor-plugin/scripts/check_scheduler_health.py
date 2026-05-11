from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def _task_status(task_name: str) -> dict[str, Any]:
    if not task_name:
        return {"checked": False, "status": "not-configured", "message": "No task name supplied."}
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"Get-ScheduledTask -TaskName '{task_name}' -ErrorAction Stop | Select-Object TaskName,State | ConvertTo-Json -Compress",
    ]
    proc = subprocess.run(command, text=True, capture_output=True)
    if proc.returncode != 0:
        return {"checked": True, "status": "missing", "taskName": task_name, "error": proc.stderr.strip()[-500:]}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {"raw": proc.stdout.strip()}
    return {"checked": True, "status": "present", "taskName": task_name, "task": payload}


def assess(manifest: Path, lock_file: Path | None, task_name: str = "") -> dict[str, Any]:
    manifest_payload = _read_json(manifest)
    steps = manifest_payload.get("steps", [])
    failed = [s for s in steps if s.get("status") != "ok"]
    lock_status = "not-configured"
    if lock_file:
        lock_status = "stale-or-active" if lock_file.exists() else "clear"
    status = "green"
    findings = []
    if not manifest.exists():
        status = "red"
        findings.append("Pipeline manifest is missing.")
    elif manifest_payload.get("status") != "ok":
        status = "red"
        findings.append(f"Last pipeline status is {manifest_payload.get('status')}.")
    if failed:
        status = "red"
        findings.append(f"{len(failed)} pipeline step(s) are not ok.")
    if lock_status == "stale-or-active":
        status = "amber" if status == "green" else status
        findings.append("Lock file exists; verify whether a run is active or stale.")
    task = _task_status(task_name)
    if task_name and task.get("status") != "present":
        status = "amber" if status == "green" else status
        findings.append("Scheduled task is not present.")
    return {
        "checkedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "manifest": str(manifest),
        "manifestStatus": manifest_payload.get("status", "missing"),
        "lastFinishedAt": manifest_payload.get("finishedAt", ""),
        "stepCount": len(steps),
        "failedSteps": [{"name": s.get("name"), "status": s.get("status"), "exitCode": s.get("exitCode")} for s in failed],
        "lockFile": str(lock_file) if lock_file else "",
        "lockStatus": lock_status,
        "task": task,
        "findings": findings,
        "nextAction": "Install or repair scheduler, clear stale lock only after confirming no active run, then execute a dry-run pipeline." if status != "green" else "Scheduler health is acceptable.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AXPA scheduler and last pipeline health.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--lock-file")
    parser.add_argument("--task-name", default="")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = assess(Path(args.manifest), Path(args.lock_file) if args.lock_file else None, args.task_name)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] in {"green", "amber"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
