from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(path), "status": "invalid-json", "error": str(exc)}
    payload.setdefault("exists", True)
    payload.setdefault("path", str(path))
    return payload


def _grade(statuses: list[str]) -> str:
    if any(s == "red" for s in statuses):
        return "red"
    if any(s == "amber" for s in statuses):
        return "amber"
    if statuses:
        return "green"
    return "unknown"


def collect(root: str | Path, prefix: str = "") -> dict[str, Any]:
    base = Path(root)

    def pick(suffix: str) -> Path:
        if prefix:
            candidate = base / f"{prefix}-{suffix}"
            if candidate.exists():
                return candidate
        matches = sorted(base.glob(f"*-{suffix}"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
        return matches[0] if matches else base / f"{prefix + '-' if prefix else ''}{suffix}"

    scheduler = _read(pick("scheduler-health.json"))
    push = _read(pick("push-readiness.json"))
    admin = _read(pick("admin-gate-preflight.json"))
    dashboard = _read(pick("dashboard-http-qa.json"))
    readiness = _read(pick("production-readiness-pack.json"))
    components = {
        "scheduler": {
            "status": scheduler.get("status", "missing"),
            "summary": f"manifest={scheduler.get('manifestStatus', 'n/a')} task={scheduler.get('task', {}).get('status', 'n/a')}",
            "path": scheduler.get("path"),
        },
        "push": {
            "status": push.get("status", "missing"),
            "summary": f"readyTargets={push.get('readyTargets', 0)}/{push.get('targetCount', 0)} auditRecords={push.get('audit', {}).get('records', 0)}",
            "path": push.get("path"),
        },
        "adminGate": {
            "status": admin.get("status", "missing"),
            "summary": f"goNoGo={admin.get('goNoGo', 'n/a')} executable={admin.get('executableCount', 0)}",
            "path": admin.get("path"),
        },
        "dashboardHttpQa": {
            "status": "green" if dashboard.get("ok") else "red" if dashboard.get("exists") else "missing",
            "summary": f"http={dashboard.get('status', 'n/a')} ok={dashboard.get('ok', False)}",
            "path": dashboard.get("path"),
        },
        "readinessPack": {
            "status": "green" if readiness.get("steps") else "missing",
            "summary": f"steps={', '.join((readiness.get('steps') or {}).keys()) if isinstance(readiness.get('steps'), dict) else 'n/a'}",
            "path": readiness.get("path"),
        },
    }
    statuses = [str(v["status"]) for v in components.values() if v["status"] != "missing"]
    blockers = [name for name, item in components.items() if item["status"] in {"red", "missing"}]
    return {
        "root": str(base),
        "prefix": prefix,
        "status": _grade(statuses),
        "componentCount": len(components),
        "blockers": blockers,
        "components": components,
        "raw": {
            "scheduler": scheduler,
            "push": push,
            "adminGate": admin,
            "dashboardHttpQa": dashboard,
            "readinessPack": readiness,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect AXPA operational preflight outputs into one status file.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = collect(args.root, args.prefix)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] in {"green", "amber", "unknown"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
