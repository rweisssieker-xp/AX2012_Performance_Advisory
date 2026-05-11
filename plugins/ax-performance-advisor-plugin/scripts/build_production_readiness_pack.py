from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def env_status(names: list[str]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in names}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a concrete AXPA production readiness pack for scheduler, push, trace, admin gates and dashboard QA.")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--dashboard")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    evidence = Path(args.evidence)
    out = Path(args.out)
    dashboard = Path(args.dashboard) if args.dashboard else out / f"{args.environment}-dashboard.html"
    push_env = {
        "teams": ["AXPA_TEAMS_WEBHOOK_URL"],
        "ado": ["AXPA_ADO_ORG", "AXPA_ADO_PROJECT", "AXPA_ADO_TOKEN"],
        "jira": ["AXPA_JIRA_BASE_URL", "AXPA_JIRA_PROJECT", "AXPA_JIRA_EMAIL", "AXPA_JIRA_TOKEN"],
        "servicenow": ["AXPA_SN_INSTANCE_URL", "AXPA_SN_TOKEN"],
        "powerbi": ["AXPA_POWERBI_ENDPOINT"],
    }
    pack = {
        "environment": args.environment,
        "server": args.server,
        "database": args.database,
        "evidence": str(evidence),
        "out": str(out),
        "steps": {
            "dashboardHttpQa": {
                "status": "ready",
                "command": f"python scripts/qa_dashboard_http.py --root . --dashboard {dashboard} --output {out / (args.environment + '-dashboard-qa.json')}",
                "purpose": "Avoid file:// browser policy issues by serving the static dashboard through local HTTP.",
            },
            "scheduler": {
                "status": "ready-to-install",
                "command": f"powershell scripts/install_windows_task.ps1 -Environment {args.environment} -Server {args.server} -Database {args.database} -Evidence {evidence} -Out {out}",
                "validation": f"python scripts/run_axpa_pipeline.py --environment {args.environment} --server {args.server} --database {args.database} --evidence {evidence} --out {out} --dry-run",
                "healthcheck": f"python scripts/check_scheduler_health.py --manifest {out / (args.environment + '-pipeline-manifest.json')} --lock-file {out / (args.environment + '.lock')} --task-name AXPA-{args.environment} --output {out / (args.environment + '-scheduler-health.json')}",
            },
            "traceAttribution": {
                "status": "needs-source-file" if not any((evidence / name).exists() and (evidence / name).stat().st_size > 3 for name in ["trace_parser.csv", "dynamicsperf.csv", "ax_model_mapping.csv"]) else "ready",
                "expectedFiles": ["trace_parser.csv", "dynamicsperf.csv", "ax_model_mapping.csv"],
                "commands": [
                    f"python scripts/import_trace_parser_export.py --input <trace-parser-export.csv> --output {evidence / 'trace_parser.csv'}",
                    f"python scripts/import_dynamicsperf_export.py --input <dynamicsperf-export.csv> --output {evidence / 'dynamicsperf.csv'}",
                    f"powershell scripts/collect_ax_model_mapping.ps1 -ConnectionString <model-db-readonly> -OutputDirectory {evidence}",
                ],
            },
            "productivePush": {
                "status": "ready-when-env-present",
                "targets": {target: env_status(names) for target, names in push_env.items()},
                "preflight": f"python scripts/validate_push_readiness.py --targets teams,ado,jira,servicenow,powerbi --audit-db {out / (args.environment + '-push-audit.sqlite')} --output {out / (args.environment + '-push-readiness.json')}",
                "dryRun": f"python scripts/push_integrations.py --evidence {evidence} --targets teams,ado,jira,servicenow,powerbi --audit-db {out / (args.environment + '-push-audit.sqlite')} --dry-run",
                "liveRun": f"python scripts/push_integrations.py --evidence {evidence} --targets teams,ado,jira,servicenow,powerbi --audit-db {out / (args.environment + '-push-audit.sqlite')}",
            },
            "adminExecutionGate": {
                "status": "preview-only-ready",
                "stateFile": str(out / f"{args.environment}-recommendation-lifecycle-state.json"),
                "approveExample": f"python scripts/manage_recommendation_lifecycle.py --state-file {out / (args.environment + '-recommendation-lifecycle-state.json')} --finding-id <finding-id> --state approved --actor <admin>",
                "preflight": f"python scripts/admin_gate_preflight.py --evidence {evidence} --output-dir {out / (args.environment + '-admin-execution')} --environment TEST --output {out / (args.environment + '-admin-gate-preflight.json')}",
                "rule": "Execution stays external; AXPA only creates gated review actions, audit state and validation requirements.",
            },
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "steps": list(pack["steps"].keys())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
