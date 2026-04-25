from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from axpa_core import (
    analyze_evidence,
    build_report,
    compare_baseline,
    export_evidence_pack,
    export_powerbi_dataset,
    write_json,
)


TOOLS = [
    {
        "name": "analyze_evidence",
        "description": "Analyze an AXPA evidence directory and return normalized findings.",
        "inputSchema": {
            "type": "object",
            "properties": {"evidence": {"type": "string"}},
            "required": ["evidence"],
        },
    },
    {
        "name": "generate_report",
        "description": "Generate a Markdown AX performance report from an evidence directory.",
        "inputSchema": {
            "type": "object",
            "properties": {"evidence": {"type": "string"}, "output": {"type": "string"}},
            "required": ["evidence", "output"],
        },
    },
    {
        "name": "export_evidence_pack",
        "description": "Create a ZIP evidence pack with raw evidence and generated findings.",
        "inputSchema": {
            "type": "object",
            "properties": {"evidence": {"type": "string"}, "output": {"type": "string"}},
            "required": ["evidence", "output"],
        },
    },
    {
        "name": "export_powerbi_dataset",
        "description": "Export a CSV dataset suitable for Power BI import.",
        "inputSchema": {
            "type": "object",
            "properties": {"evidence": {"type": "string"}, "output": {"type": "string"}},
            "required": ["evidence", "output"],
        },
    },
    {
        "name": "compare_baseline",
        "description": "Compare before and after evidence directories for risk-score change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "before": {"type": "string"},
                "after": {"type": "string"},
                "output": {"type": "string"},
            },
            "required": ["before", "after", "output"],
        },
    },
    {
        "name": "export_ticket_backlog",
        "description": "Export findings as Jira/Azure DevOps compatible CSV backlog.",
        "inputSchema": {
            "type": "object",
            "properties": {"evidence": {"type": "string"}, "output": {"type": "string"}, "system": {"type": "string"}},
            "required": ["evidence", "output"],
        },
    },
    {
        "name": "run_script",
        "description": "Run an allowlisted AXPA Python script by name with arguments.",
        "inputSchema": {
            "type": "object",
            "properties": {"script": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}}},
            "required": ["script"],
        },
    },
]

SCRIPT_DIR = Path(__file__).resolve().parent
ALLOWED_SCRIPTS = {path.name for path in SCRIPT_DIR.glob("*.py") if path.name not in {"mcp_server.py"}}


def content(payload: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]}


def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "analyze_evidence":
        return content(analyze_evidence(args["evidence"]))
    if name == "generate_report":
        report = build_report(args["evidence"])
        output = Path(args["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        return content({"output": str(output), "bytes": len(report.encode("utf-8"))})
    if name == "export_evidence_pack":
        path = export_evidence_pack(args["evidence"], args["output"])
        return content({"output": str(path)})
    if name == "export_powerbi_dataset":
        path = export_powerbi_dataset(args["evidence"], args["output"])
        return content({"output": str(path)})
    if name == "compare_baseline":
        result = compare_baseline(args["before"], args["after"])
        write_json(Path(args["output"]), result)
        return content({"output": args["output"], "result": result})
    if name == "export_ticket_backlog":
        import csv
        findings = analyze_evidence(args["evidence"])
        output = Path(args["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "Title": f"{item['id']} {item['title']}",
                "Work Item Type": "Issue" if args.get("system", "azure-devops") == "azure-devops" else "Task",
                "Description": item["recommendation"]["summary"],
                "Priority": item["severity"],
                "Tags": f"AXPA;{item['classification']};{item['axContext'].get('module', 'Unknown')}",
                "Assigned To": item["axContext"].get("technicalOwner", ""),
                "Acceptance Criteria": item["validation"].get("successMetric", ""),
            }
            for item in findings
        ]
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["Title"])
            writer.writeheader()
            writer.writerows(rows)
        return content({"output": str(output), "rows": len(rows)})
    if name == "run_script":
        script = args["script"]
        if script not in ALLOWED_SCRIPTS:
            raise ValueError(f"Script is not allowlisted: {script}")
        cmd = [sys.executable, str(SCRIPT_DIR / script), *[str(item) for item in args.get("args", [])]]
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
        return content({"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
    raise ValueError(f"Unknown tool: {name}")


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ax-performance-advisor", "version": "0.1.0"},
            }
        elif method == "notifications/initialized":
            return None
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = request.get("params", {})
            result = call_tool(params.get("name", ""), params.get("arguments", {}))
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        response = handle(json.loads(line))
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
