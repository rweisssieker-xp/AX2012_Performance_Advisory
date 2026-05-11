from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

WRITE_VERBS = {"INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "ALTER", "DROP", "TRUNCATE"}
RISKY_PERMISSIONS = {"can_create_table", "can_alter_any_schema"}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _is_readonly_permission_check(line: str, verb: str) -> bool:
    return verb in {"CREATE", "ALTER"} and "HAS_PERMS_BY_NAME" in line.upper()


def _is_dynamic_select_wrapper(line: str, verb: str) -> bool:
    if verb != "EXEC":
        return False
    upper = line.upper()
    return "SP_EXECUTESQL" in upper


def _scan_script(path: Path) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        for verb in WRITE_VERBS:
            if not re.search(rf"\b{verb}\b", stripped, flags=re.IGNORECASE):
                continue
            if _is_readonly_permission_check(stripped, verb) or _is_dynamic_select_wrapper(stripped, verb):
                continue
            hits.append({"file": path.name, "line": line_no, "verb": verb, "text": stripped[:220]})
    return hits


def _permission_rows(evidence: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name in ["permissions.csv", "sql_permissions.csv"]:
        rows.extend(_read_csv(evidence / name))
    return rows


def generate_safety_guard(evidence: str | Path, scripts_dir: str | Path, output_dir: str | Path | None = None) -> dict[str, Any]:
    evidence_path = Path(evidence)
    scripts_path = Path(scripts_dir)
    write_hits: list[dict[str, Any]] = []
    for path in sorted(scripts_path.glob("collect_*.ps1")):
        write_hits.extend(_scan_script(path))

    permissions = _permission_rows(evidence_path)
    risky = [
        str(row.get("permission"))
        for row in permissions
        if str(row.get("permission")) in RISKY_PERMISSIONS and str(row.get("value")) == "1"
    ]

    if write_hits:
        verdict = "red"
        collector_mode = "blocked"
    elif risky:
        verdict = "amber"
        collector_mode = "read-only"
    else:
        verdict = "green"
        collector_mode = "read-only"

    payload = {
        "verdict": verdict,
        "collectorMode": collector_mode,
        "localOnly": True,
        "databaseWritesAllowed": False,
        "riskyPermissions": risky,
        "writeVerbHits": write_hits,
        "permissionRows": permissions,
        "outputPolicy": "AXPA writes local evidence/out/docs files only. Queried AX and SQL databases stay read-only.",
        "nextAction": "Use a restricted read-only SQL login for scheduled production runs." if risky else "Continue with read-only collectors.",
    }
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "safety-guard.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA read-only safety guard.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--scripts-dir", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    payload = generate_safety_guard(args.evidence, args.scripts_dir, args.output_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["verdict"] != "red" else 1


if __name__ == "__main__":
    raise SystemExit(main())
