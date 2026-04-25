from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROLE_SECTIONS = {
    "viewer": ["Executive Narrative", "Top Root Causes", "Top Findings"],
    "dba": ["Top Root Causes", "Empfohlene Playbooks", "Admin Execution Preview", "Enterprise Observability"],
    "ax-admin": ["AX Module / Business Domain", "Implementation Q&A", "Admin Execution Preview"],
    "qa-gxp": ["GxP Validation Assistant", "Evidence Gaps", "Realization Pack", "Admin Execution Preview"],
    "cio": ["Executive Narrative", "AI/KI Feature Coverage", "Enterprise Observability"],
    "admin": ["all"]
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate role-specific static dashboard entry points.")
    parser.add_argument("--dashboard", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--rbac", default="")
    args = parser.parse_args()
    html = Path(args.dashboard).read_text(encoding="utf-8")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    for role, sections in ROLE_SECTIONS.items():
        banner = f"<div style='padding:10px 24px;background:#101828;color:white;font-family:Segoe UI'>Role view: <b>{role}</b> | Allowed sections: {', '.join(sections)}</div>"
        role_html = html.replace("<body>", f"<body>{banner}", 1)
        role_html = role_html.replace("AX Performance Advisor</title>", f"AX Performance Advisor - {role}</title>")
        path = out / f"dashboard-{role}.html"
        path.write_text(role_html, encoding="utf-8")
        index[role] = str(path)
    (out / "rbac-index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote RBAC portal views to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
