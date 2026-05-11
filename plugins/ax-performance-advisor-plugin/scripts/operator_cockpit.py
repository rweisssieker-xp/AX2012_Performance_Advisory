from __future__ import annotations

from typing import Any

SEV = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _rank(finding: dict[str, Any]) -> tuple[int, int, int]:
    return (
        SEV.get(str(finding.get("severity")), 1),
        1 if finding.get("confidence") == "high" else 0,
        len(finding.get("evidence", [])),
    )


def _context_from(finding: dict[str, Any]) -> dict[str, list[str]]:
    ax = finding.get("axContext") or {}
    frontend = finding.get("frontendContext") or {}
    return {
        "users": sorted({str(frontend.get("user") or "")} - {""}),
        "hosts": sorted({str(frontend.get("host") or "")} - {""}),
        "sessions": sorted({str(frontend.get("sessionId") or "")} - {""}),
        "aos": sorted({str(x) for x in ax.get("aos", []) if str(x)}),
        "tables": sorted({str(x) for x in ax.get("tables", []) if str(x)}),
        "batchGroups": sorted({str(x) for x in ax.get("batchJobs", []) if str(x)}),
    }


def _safe_actions(finding: dict[str, Any]) -> list[str]:
    playbook = (finding.get("recommendation") or {}).get("playbook", "")
    if playbook == "ax-frontend-machine-impact":
        return [
            "Confirm whether the user action is intentional before stopping anything.",
            "Ask the user to narrow Item/Site/Warehouse/Batch filters and rerun in TEST.",
            "Capture another five-minute lightweight flight recording if the issue is still active.",
        ]
    if "batch" in playbook:
        return [
            "Review the proposed batch move in TEST only.",
            "Compare source and target hour peak concurrency after the simulated move.",
            "Check downstream dependencies before changing recurrence time.",
        ]
    return [
        "Preserve current evidence and compare against a follow-up snapshot.",
        "Validate recommendation in TEST before any production change.",
        "Create a local ticket draft with evidence, risk, validation and rollback.",
    ]


def generate_operator_cockpit(
    findings: list[dict[str, Any]],
    safety_guard: dict[str, Any],
    evidence_health: dict[str, Any],
    operational_status: dict[str, Any],
) -> dict[str, Any]:
    top = sorted(findings, key=_rank, reverse=True)[0] if findings else {}
    context = _context_from(top) if top else {"users": [], "hosts": [], "sessions": [], "aos": [], "tables": [], "batchGroups": []}
    high_count = sum(1 for f in findings if f.get("severity") in {"critical", "high"})
    return {
        "status": "active" if findings else "clear",
        "findingCount": len(findings),
        "highOrCriticalCount": high_count,
        "safetyVerdict": safety_guard.get("verdict", "unknown"),
        "operationalStatus": operational_status.get("status", "unknown"),
        "evidenceScore": evidence_health.get("score", "unknown"),
        "topSuspect": {
            "findingId": top.get("id", ""),
            "title": top.get("title", "No active finding"),
            "severity": top.get("severity", "informational"),
            "confidence": top.get("confidence", "unknown"),
            "module": (top.get("axContext") or {}).get("module", "Unknown"),
            "playbook": (top.get("recommendation") or {}).get("playbook", ""),
            "why": top.get("likelyCause") or (top.get("recommendation") or {}).get("summary", ""),
        },
        "affectedContext": context,
        "safeNextActions": _safe_actions(top) if top else ["Run a read-only snapshot and review the dashboard."],
        "doNotDo": [
            "Do not write to the queried AX or SQL database from AXPA.",
            "Do not create indexes directly from missing-index DMV output.",
            "Do not kill sessions without owner confirmation and operations approval.",
        ],
        "evidenceMissing": [
            "Trace Parser or DynamicsPerf export for exact X++ call tree.",
            "AX model mapping for class and method attribution.",
        ],
    }
