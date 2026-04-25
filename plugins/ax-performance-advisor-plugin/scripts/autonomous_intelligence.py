from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def evidence_scout(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    available = {p.name for p in root.glob("*") if p.is_file()}
    scout = []
    requirements = {
        "trace_parser.csv": "Needed for exact X++ class/method attribution.",
        "dynamicsperf_trace.csv": "Needed for historical DynamicsPerf correlation.",
        "deadlocks.csv": "Needed for deadlock graph root cause.",
        "batch_jobs.csv": "Needed for batch schedule collision proof.",
        "user_sessions.csv": "Needed for affected-user correlation.",
        "sqlplan XML": "Needed for operator-level plan diff and spill/lookup analysis.",
    }
    for source, reason in requirements.items():
        present = any(source.lower().replace(" xml", "") in name.lower() for name in available)
        scout.append({"source": source, "present": present, "whyItMatters": reason, "collectionMode": "read-only/import"})
    return {"sources": scout, "nextBestEvidence": [s for s in scout if not s["present"]][:3]}


def investigation_tree(findings: list[dict[str, Any]]) -> dict[str, Any]:
    top = sorted(findings, key=lambda f: RANK.get(f.get("severity"), 0), reverse=True)[:8]
    nodes = []
    for f in top:
        playbook = f.get("recommendation", {}).get("playbook", "review")
        nodes.append({
            "findingId": f["id"],
            "question": f"Is {playbook} the real driver for {f['title']}?",
            "yes": f"Validate with {f.get('validation', {}).get('successMetric', 'before/after evidence')}",
            "no": "Collect missing evidence and test alternative root cause.",
            "nextEvidence": [e.get("source", "") for e in f.get("evidence", [])[:3]],
        })
    return {"rootQuestion": "Which evidence-backed cause should be handled first?", "nodes": nodes}


def root_cause_debate(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    rows = []
    for playbook, count in groups.most_common(8):
        related = [f for f in findings if f.get("recommendation", {}).get("playbook") == playbook]
        rows.append({
            "hypothesis": playbook,
            "argumentFor": f"{count} findings support this hypothesis; top severity {max((f.get('severity') for f in related), default='unknown')}.",
            "argumentAgainst": "May be a symptom rather than cause unless time-window and owner evidence align.",
            "decidingEvidence": "Comparable time-window correlation plus post-change validation.",
        })
    return rows


def recommendation_quality_gate(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for f in findings:
        checks = {
            "hasEvidence": bool(f.get("evidence")),
            "hasRollback": bool(f.get("validation", {}).get("rollback")),
            "hasSuccessMetric": bool(f.get("validation", {}).get("successMetric")),
            "hasOwner": bool(f.get("axContext", {}).get("technicalOwner")),
            "hasApprovalPath": bool(f.get("changeReadiness", {}).get("approvalPath")),
        }
        passed = sum(1 for v in checks.values() if v)
        rows.append({"findingId": f["id"], "score": passed, "status": "pass" if passed == len(checks) else "needs-work", "checks": checks})
    return {"passCount": sum(1 for r in rows if r["status"] == "pass"), "items": rows}


def kpi_storyboard(findings: list[dict[str, Any]]) -> dict[str, Any]:
    sev = Counter(f.get("severity") for f in findings)
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    return {
        "slides": [
            {"title": "Current Risk", "message": f"{len(findings)} findings, {sev['high'] + sev['critical']} high/critical."},
            {"title": "Dominant Themes", "message": ", ".join(k for k, _ in playbooks.most_common(5))},
            {"title": "Decision", "message": "Approve TEST validation and evidence completion for the top risk groups."},
            {"title": "Proof", "message": "Use before/after AXPA run, evidence pack, and release gate status."},
        ]
    }


def anonymized_pattern_library(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in findings:
        rows.append({
            "patternId": f"PAT-{f['id'][-8:]}",
            "severity": f.get("severity"),
            "playbook": f.get("recommendation", {}).get("playbook", "review"),
            "module": f.get("axContext", {}).get("module", "Unknown"),
            "evidenceTypes": [e.get("source", "") for e in f.get("evidence", [])],
            "recommendationClass": f.get("classification", ""),
        })
    return rows


def generate_autonomous_intelligence(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "evidenceScout": evidence_scout(evidence),
        "investigationTree": investigation_tree(findings),
        "rootCauseDebate": root_cause_debate(findings),
        "recommendationQualityGate": recommendation_quality_gate(findings),
        "kpiStoryboard": kpi_storyboard(findings),
        "anonymizedPatternLibrary": anonymized_pattern_library(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate autonomous AXPA intelligence artifacts.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_autonomous_intelligence(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote autonomous intelligence pack to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
