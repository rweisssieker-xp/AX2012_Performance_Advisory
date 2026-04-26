from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from axpa_core import write_json


PRIMARY_KEYWORDS = {
    "daily-health-check",
    "sql-server-query-tuning",
    "ax-performance-analysis",
    "blocking-analysis",
    "index-risk-review",
    "autonomous-ops-copilot",
    "management-report-generator",
    "admin-execution-mode",
    "evidence-pack-audit",
    "traceparser-dynamicsperf-analysis",
}


def generate_skill_catalog(plugin_root: str | Path) -> dict[str, Any]:
    root = Path(plugin_root)
    skills_root = root / "skills"
    groups: dict[str, list[dict[str, str]]] = {
        "Primary": [],
        "SQL Diagnostics": [],
        "AX/AOS Diagnostics": [],
        "AI/KI": [],
        "Governance": [],
        "Execution/Admin": [],
        "Reporting/Export": [],
        "Advanced": [],
    }
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        desc = ""
        for line in text.splitlines():
            if line.startswith("description:"):
                desc = line.split(":", 1)[1].strip().strip('"')
                break
        item = {"name": skill_dir.name, "description": desc}
        name = skill_dir.name
        if name in PRIMARY_KEYWORDS:
            groups["Primary"].append(item)
        elif any(k in name for k in ["sql", "query", "index", "tempdb", "statistics", "blocking", "parameter"]):
            groups["SQL Diagnostics"].append(item)
        elif any(k in name for k in ["ax", "aos", "batch", "xpp", "traceparser", "dynamicsperf"]):
            groups["AX/AOS Diagnostics"].append(item)
        elif name.startswith("ai-") or "autonomous" in name or "learning" in name or "rag" in name:
            groups["AI/KI"].append(item)
        elif any(k in name for k in ["governance", "approval", "itil", "gxp", "release", "debt"]):
            groups["Governance"].append(item)
        elif any(k in name for k in ["admin", "execution", "portal", "agent"]):
            groups["Execution/Admin"].append(item)
        elif any(k in name for k in ["report", "powerbi", "ticket", "export"]):
            groups["Reporting/Export"].append(item)
        else:
            groups["Advanced"].append(item)
    return {"skillCount": sum(len(v) for v in groups.values()), "groups": groups}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate grouped AXPA skill catalog.")
    parser.add_argument("--plugin-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    write_json(args.output, generate_skill_catalog(args.plugin_root))
    print(f"Wrote skill catalog to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
