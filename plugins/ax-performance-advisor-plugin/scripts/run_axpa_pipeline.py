from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_step(name: str, command: list[str], cwd: Path, dry_run: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    row: dict[str, Any] = {
        "name": name,
        "command": " ".join(command),
        "startedAt": now_iso(),
        "status": "dry-run" if dry_run else "running",
        "durationSeconds": 0,
        "stdout": "",
        "stderr": "",
    }
    if dry_run:
        return row
    proc = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True)
    row["durationSeconds"] = round(time.perf_counter() - started, 2)
    row["stdout"] = proc.stdout[-4000:]
    row["stderr"] = proc.stderr[-4000:]
    row["exitCode"] = proc.returncode
    row["status"] = "ok" if proc.returncode == 0 else "failed"
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {proc.returncode}: {proc.stderr[-1000:]}")
    return row


def artifacts_for(*roots: Path) -> list[dict[str, Any]]:
    rows = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rows.append(
                    {
                        "path": str(path),
                        "name": path.name,
                        "bytes": path.stat().st_size,
                        "modifiedAt": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
                    }
                )
    return rows


def write_metadata(evidence: Path, environment: str, server: str, database: str) -> None:
    metadata_path = evidence / "metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    metadata.update(
        {
            "environment": environment,
            "sqlServer": server,
            "axDatabase": database,
            "pipelineUpdatedAt": now_iso(),
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def acquire_lock(path: Path, stale_minutes: int) -> None:
    if path.exists():
        age_seconds = time.time() - path.stat().st_mtime
        if age_seconds < stale_minutes * 60:
            raise RuntimeError(f"Pipeline lock exists: {path}")
    path.write_text(json.dumps({"pid": os.getpid(), "createdAt": now_iso()}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AXPA read-only collection, analysis, dashboard, AI/KI and trend pipeline.")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--connection-string")
    parser.add_argument("--collect", action="store_true", help="Run SQL and AX collectors before analysis.")
    parser.add_argument("--wait-delta-seconds", type=int, default=10)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--trend-db")
    parser.add_argument("--lock-file")
    parser.add_argument("--stale-lock-minutes", type=int, default=240)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    evidence = Path(args.evidence)
    output = Path(args.out)
    evidence.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    trend_db = Path(args.trend_db) if args.trend_db else output / f"{args.environment}-trends.sqlite"
    lock_file = Path(args.lock_file) if args.lock_file else output / f"{args.environment}.lock"
    connection = args.connection_string or f"Server={args.server};Database={args.database};Integrated Security=True;Application Name=AXPA-Pipeline;TrustServerCertificate=True"
    env = os.environ.copy()
    env["AXPA_ENVIRONMENT_NAME"] = args.environment

    manifest: dict[str, Any] = {
        "environment": args.environment,
        "server": args.server,
        "database": args.database,
        "mode": "read-only-advisory",
        "startedAt": now_iso(),
        "collect": args.collect,
        "steps": [],
        "artifacts": [],
        "status": "running",
        "lockFile": str(lock_file),
    }

    try:
        if not args.dry_run:
            acquire_lock(lock_file, args.stale_lock_minutes)
        if args.collect:
            collect_sql = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPTS / "collect_sql_snapshot.ps1"),
                "-ConnectionString",
                connection,
                "-OutputDirectory",
                str(evidence),
                "-AxDatabaseName",
                args.database,
                "-IncludeQueryStore",
                "-IncludeDeadlocks",
                "-WaitDeltaSeconds",
                str(args.wait_delta_seconds),
            ]
            manifest["steps"].append(run_step("collect-sql", collect_sql, ROOT, args.dry_run))
            collect_ax = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(SCRIPTS / "collect_ax_db_snapshot.ps1"),
                "-ConnectionString",
                connection,
                "-OutputDirectory",
                str(evidence),
                "-Days",
                str(args.days),
            ]
            manifest["steps"].append(run_step("collect-ax", collect_ax, ROOT, args.dry_run))
        if not args.dry_run:
            write_metadata(evidence, args.environment, args.server, args.database)

        commands = [
            ("analyze", [sys.executable, str(SCRIPTS / "analyze_evidence.py"), "--evidence", str(evidence), "--output", str(output / f"{args.environment}-findings.json")]),
            ("report", [sys.executable, str(SCRIPTS / "generate_report.py"), "--evidence", str(evidence), "--output", str(output / f"{args.environment}-technical-report.md")]),
            ("dashboard", [sys.executable, str(SCRIPTS / "generate_dashboard.py"), "--evidence", str(evidence), "--output", str(output / f"{args.environment}-dashboard.html")]),
            ("autonomous-ops", [sys.executable, str(SCRIPTS / "autonomous_ops.py"), "--evidence", str(evidence), "--output", str(output / f"{args.environment}-autonomous-ops.json")]),
            ("ai-ki", [sys.executable, str(SCRIPTS / "ai_ki_extensions.py"), "--evidence", str(evidence), "--output", str(output / f"{args.environment}-ai-ki-extensions.json")]),
            ("trend-store", [sys.executable, str(SCRIPTS / "update_trend_store.py"), "--evidence", str(evidence), "--db", str(trend_db)]),
            ("platform-extensions", [sys.executable, str(SCRIPTS / "platform_extensions.py"), "--evidence", str(evidence), "--output-dir", str(output / f"{args.environment}-platform"), "--trend-db", str(trend_db), "--manifest", str(output / f"{args.environment}-pipeline-manifest.json"), "--state-file", str(output / f"{args.environment}-recommendation-lifecycle-state.json")]),
        ]
        for name, command in commands:
            manifest["steps"].append(run_step(name, command, ROOT, args.dry_run))
        manifest["status"] = "ok"
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = str(exc)
    finally:
        manifest["finishedAt"] = now_iso()
        manifest["artifacts"] = artifacts_for(evidence, output)
        manifest_path = output / f"{args.environment}-pipeline-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if lock_file.exists() and not args.dry_run:
            lock_file.unlink()
        print(f"Wrote pipeline manifest to {manifest_path}")
    return 0 if manifest["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
