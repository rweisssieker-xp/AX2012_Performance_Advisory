from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


def _top(findings: list[dict[str, Any]], n: int = 20) -> list[dict[str, Any]]:
    rank = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}
    return sorted(findings, key=lambda f: rank.get(f.get("severity"), 0), reverse=True)[:n]


def runbook_automation(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in _top(findings, 12):
        playbook = f.get("recommendation", {}).get("playbook", "review")
        rows.append(
            {
                "findingId": f["id"],
                "playbook": playbook,
                "steps": [
                    "Freeze current evidence pack and record timestamp.",
                    f"Assign owner: {f.get('axContext', {}).get('technicalOwner', 'AX Operations')}.",
                    f"Run diagnostic playbook: {playbook}.",
                    "Execute TEST validation only; do not change PROD from dashboard.",
                    f"Success metric: {f.get('validation', {}).get('successMetric', 'Compare before/after evidence')}.",
                    f"Rollback note: {f.get('validation', {}).get('rollback', 'Rollback through change control')}.",
                ],
            }
        )
    return rows


def raci_matrix(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = defaultdict(list)
    for f in findings:
        owner = f.get("axContext", {}).get("technicalOwner", "AX Operations")
        grouped[owner].append(f)
    return [
        {
            "owner": owner,
            "responsible": owner,
            "accountable": "AX Platform Owner",
            "consulted": "DBA, Business Process Owner, QA/GxP when applicable",
            "informed": "CIO/IT Operations",
            "findingCount": len(items),
            "highCount": sum(1 for f in items if f.get("severity") in {"critical", "high"}),
        }
        for owner, items in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
    ]


def business_impact_timeline(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = defaultdict(list)
    for f in findings:
        window = f.get("timeWindow", {}) or {}
        label = window.get("start")[:13] if window.get("start") else "current-evidence-window"
        buckets[label].append(f)
    return [
        {
            "window": window,
            "findingCount": len(items),
            "highCount": sum(1 for f in items if f.get("severity") in {"critical", "high"}),
            "modules": [name for name, _ in Counter(f.get("axContext", {}).get("module", "Unknown") for f in items).most_common(5)],
            "businessImpact": [f.get("businessImpact", {}).get("impact", "") for f in _top(items, 3)],
        }
        for window, items in buckets.items()
    ]


def suppression_governance(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    grouped = Counter((f.get("recommendation", {}).get("playbook", "review"), f.get("axContext", {}).get("module", "Unknown")) for f in findings)
    for (playbook, module), count in grouped.most_common():
        if count < 3:
            continue
        candidates.append(
            {
                "scope": f"{playbook}:{module}",
                "findingCount": count,
                "recommendedAction": "Review for grouping/suppression only after owner approval; do not hide high-risk findings by default.",
                "expiry": "30 days",
                "requiresApproval": True,
            }
        )
    return candidates


def data_quality_checks(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(evidence)
    files = list(root.glob("*"))
    empty = [p.name for p in files if p.is_file() and p.stat().st_size == 0]
    errors = [p.name for p in files if p.name.endswith(".error.csv")]
    duplicate_ids = [item for item, count in Counter(f["id"] for f in findings).items() if count > 1]
    return {
        "fileCount": len([p for p in files if p.is_file()]),
        "emptyFiles": empty,
        "collectorErrors": errors,
        "duplicateFindingIds": duplicate_ids,
        "score": max(0, 100 - len(empty) * 3 - len(errors) * 8 - len(duplicate_ids) * 20),
    }


def audit_export(findings: list[dict[str, Any]], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "audit-findings.csv"
    json_path = out / "audit-findings.json"
    rows = []
    for f in findings:
        rows.append(
            {
                "id": f["id"],
                "title": f["title"],
                "severity": f["severity"],
                "confidence": f.get("confidence", ""),
                "owner": f.get("axContext", {}).get("technicalOwner", ""),
                "approvalPath": f.get("changeReadiness", {}).get("approvalPath", ""),
                "rollback": f.get("validation", {}).get("rollback", ""),
                "successMetric": f.get("validation", {}).get("successMetric", ""),
                "status": f.get("status", "proposed"),
            }
        )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    write_json(json_path, rows)
    return {"csv": str(csv_path), "json": str(json_path), "rows": len(rows)}


def generate_governance_extensions(evidence: str | Path, output_dir: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "runbookAutomation": runbook_automation(findings),
        "raciMatrix": raci_matrix(findings),
        "businessImpactTimeline": business_impact_timeline(findings),
        "suppressionGovernance": suppression_governance(findings),
        "dataQualityChecks": data_quality_checks(evidence, findings),
        "auditExport": audit_export(findings, Path(output_dir) / "audit-export"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA governance extension pack.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    payload = generate_governance_extensions(args.evidence, args.output_dir)
    write_json(Path(args.output_dir) / "governance-extensions.json", payload)
    print(f"Wrote governance extensions to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
