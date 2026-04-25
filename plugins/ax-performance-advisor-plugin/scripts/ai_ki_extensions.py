from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, summarize_root_causes, write_json


RANK = {"critical": 5, "high": 4, "medium": 3, "low": 2, "informational": 1}


def _top(findings: list[dict[str, Any]], n: int = 12) -> list[dict[str, Any]]:
    return sorted(findings, key=lambda f: RANK.get(f.get("severity"), 0), reverse=True)[:n]


def hypothesis_ranking(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    rows = []
    for playbook, count in groups.most_common():
        related = [f for f in findings if f.get("recommendation", {}).get("playbook") == playbook]
        severity_points = sum(RANK.get(f.get("severity"), 1) for f in related)
        evidence_points = sum(len(f.get("evidence", [])) for f in related)
        confidence = "high" if evidence_points >= count and severity_points >= count * 3 else "medium"
        rows.append(
            {
                "hypothesis": playbook,
                "findingCount": count,
                "score": severity_points + evidence_points,
                "confidence": confidence,
                "supportingFindings": [f["id"] for f in _top(related, 5)],
                "why": f"{count} findings, {severity_points} severity points, {evidence_points} evidence points.",
            }
        )
    return sorted(rows, key=lambda r: r["score"], reverse=True)


def counterfactuals(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in _top(findings, 12):
        playbook = f.get("recommendation", {}).get("playbook", "review")
        rows.append(
            {
                "findingId": f["id"],
                "ifWeDoNothing": f"Risk remains open; {f.get('businessImpact', {}).get('impact', 'business impact requires validation')}",
                "ifWeValidateInTest": f"Expected to reduce uncertainty for {playbook}; no PROD risk.",
                "ifWeImplementAfterApproval": f"Potentially reduces {playbook} risk; must prove with post-change evidence.",
                "ifItFails": f.get("validation", {}).get("rollback", "Rollback through change control and mark recommendation as rejected/deferred."),
            }
        )
    return rows


def causal_narrative(findings: list[dict[str, Any]]) -> dict[str, Any]:
    causes = summarize_root_causes(findings)[:6]
    chain = []
    for cause in causes:
        chain.append(
            {
                "cause": cause.get("playbook"),
                "module": cause.get("module"),
                "effect": f"{cause.get('count')} findings with highest severity {cause.get('highestSeverity')}",
                "nextProof": "Validate with time-window, owner, and before/after evidence.",
            }
        )
    return {"summary": "The dominant causal chain is inferred from grouped findings and evidence strength.", "chain": chain}


def llm_context_pack(findings: list[dict[str, Any]]) -> dict[str, Any]:
    top = _top(findings, 20)
    system_prompt = (
        "You are AX Performance Advisor. Answer only from provided AXPA evidence. "
        "Separate facts, inferences, risks, validation, and rollback. Never recommend blind PROD changes."
    )
    context = [
        {
            "findingId": f["id"],
            "title": f["title"],
            "severity": f["severity"],
            "confidence": f.get("confidence"),
            "evidence": f.get("evidence", []),
            "recommendation": f.get("recommendation", {}),
            "validation": f.get("validation", {}),
        }
        for f in top
    ]
    return {"systemPrompt": system_prompt, "contextFindings": context, "sourcePolicy": "Use finding IDs in every answer."}


def evidence_chunks(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks = []
    for f in findings:
        text = (
            f"Finding {f['id']}: {f['title']}. Severity {f['severity']}. "
            f"Cause: {f.get('likelyCause', '')}. Recommendation: {f.get('recommendation', {}).get('summary', '')}. "
            f"Validation: {f.get('validation', {}).get('successMetric', '')}."
        )
        chunks.append({"id": f["id"], "text": text, "metadata": {"severity": f["severity"], "playbook": f.get("recommendation", {}).get("playbook", "review")}})
    return chunks


def confidence_calibration(findings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for f in findings:
        evidence_count = len(f.get("evidence", []))
        confidence = f.get("confidence", "low")
        calibrated = "high" if evidence_count >= 2 and confidence == "high" else "medium" if evidence_count >= 1 else "low"
        rows.append({"findingId": f["id"], "declared": confidence, "calibrated": calibrated, "evidenceCount": evidence_count})
    summary = Counter(r["calibrated"] for r in rows)
    return {"summary": dict(summary), "items": rows}


def generate_ai_ki_extensions(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "hypothesisRanking": hypothesis_ranking(findings),
        "counterfactuals": counterfactuals(findings),
        "causalNarrative": causal_narrative(findings),
        "llmContextPack": llm_context_pack(findings),
        "evidenceChunks": evidence_chunks(findings),
        "confidenceCalibration": confidence_calibration(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate additional AI/KI extension artifacts.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = generate_ai_ki_extensions(args.evidence)
    write_json(args.output, payload)
    print(f"Wrote AI/KI extensions to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
