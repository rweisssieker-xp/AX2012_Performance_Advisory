from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, batch_collision_summary, load_evidence, summarize_root_causes, write_json


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


def batch_reschedule_simulator(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    batch = batch_collision_summary(load_evidence(evidence))
    group_candidates = []
    for index, group in enumerate(batch.get("groupCollisions", [])[:10], start=1):
        reduction = min(85, 20 + index * 5)
        group_candidates.append(
            {
                "groups": group["groups"],
                "currentOverlapSeconds": group["totalOverlapSeconds"],
                "collisionCount": group["collisions"],
                "proposal": f"Move one side of {group['groups']} by 15-30 minutes in TEST first.",
                "estimatedOverlapReductionPercent": reduction,
                "validationMetric": "group overlap seconds, affected batch duration, SQL wait delta, live blocking rows",
                "risk": "low" if group["totalOverlapSeconds"] < 900 else "medium",
            }
        )
    batch_findings = [f for f in findings if "batch" in (f.get("title", "") + f.get("recommendation", {}).get("playbook", "")).lower()]
    return {
        "mode": "deterministic-simulation",
        "taskCount": batch.get("taskCount", 0),
        "collisionCount": batch.get("collisionCount", 0),
        "peakConcurrency": batch.get("peakConcurrency", 0),
        "peakWindow": batch.get("peakWindow", ""),
        "candidateCount": len(group_candidates),
        "candidates": group_candidates,
        "linkedFindingIds": [f["id"] for f in _top(batch_findings, 10)],
    }


def root_cause_bridge(evidence: str | Path, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batch = batch_collision_summary(load_evidence(evidence))
    rows = []
    for group in batch.get("groupCollisions", [])[:8]:
        rows.append(
            {
                "hypothesis": f"Batch group collision {group['groups']} amplifies SQL/AOS pressure",
                "supportingEvidence": [
                    f"{group['collisions']} collisions",
                    f"{group['totalOverlapSeconds']} total overlap seconds",
                    f"max overlap {group['maxOverlapSeconds']} seconds",
                ],
                "examples": group.get("examples", [])[:4],
                "decidingTest": "Shift one group in TEST, rerun AXPA, compare overlap, waits, runtime, blocking.",
                "confidence": "high" if group["totalOverlapSeconds"] >= 900 else "medium",
            }
        )
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    for playbook, count in playbooks.most_common(5):
        rows.append(
            {
                "hypothesis": f"{playbook} is an independent or secondary driver",
                "supportingEvidence": [f"{count} findings"],
                "examples": [f["title"] for f in findings if f.get("recommendation", {}).get("playbook") == playbook][:3],
                "decidingTest": "Validate against same business window and compare before/after evidence.",
                "confidence": "medium",
            }
        )
    return rows


def next_best_evidence(findings: list[dict[str, Any]], evidence: str | Path) -> list[dict[str, Any]]:
    root = Path(evidence)
    files = {p.name.lower(): p.stat().st_size for p in root.glob("*") if p.is_file()} if root.exists() else {}
    candidates = [
        ("trace_parser.csv", "Exact SQL-to-X++ class/method attribution", "highest"),
        ("dynamicsperf.csv", "Historical AX/DynamicsPerf correlation", "high"),
        ("deadlocks.csv", "Deadlock graph proof for blocking chains", "high"),
        ("aos_counters.csv", "AOS CPU/memory/queue pressure during batch peak", "high"),
        ("ax_live_blocking.csv", "Live AX blocked worker correlation", "medium"),
        ("query_store_runtime.csv", "Query runtime and regression proof", "medium"),
    ]
    rows = []
    for filename, reason, value in candidates:
        present = filename in files and files[filename] > 0
        rows.append(
            {
                "source": filename,
                "present": present,
                "businessValue": value,
                "why": reason,
                "nextAction": "Use current evidence." if present else "Collect/import for the affected batch window.",
                "unblocks": [f["id"] for f in _top(findings, 5)],
            }
        )
    return rows


def change_roi_prioritizer(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in _top(findings, 25):
        severity = RANK.get(f.get("severity"), 1)
        confidence = 3 if f.get("confidence") == "high" else 2 if f.get("confidence") == "medium" else 1
        effort = f.get("changeReadiness", {}).get("testEffort", "medium")
        effort_penalty = {"low": 1, "medium": 2, "high": 3}.get(effort, 2)
        score = round((severity * confidence * 10) / effort_penalty, 1)
        rows.append(
            {
                "findingId": f["id"],
                "title": f["title"],
                "score": score,
                "why": f"{f.get('severity')} severity, {f.get('confidence')} confidence, {effort} effort.",
                "firstMove": f.get("recommendation", {}).get("summary", "Review evidence."),
                "approval": f.get("changeReadiness", {}).get("approvalPath", "Review"),
            }
        )
    return sorted(rows, key=lambda item: item["score"], reverse=True)


def admin_copilot_questions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions = []
    for f in _top(findings, 15):
        playbook = f.get("recommendation", {}).get("playbook", "review")
        questions.append(
            {
                "findingId": f["id"],
                "title": f["title"],
                "questions": [
                    f"Welche TEST-Umgebung bildet {playbook} realistisch ab?",
                    "Gibt es ein vergleichbares Zeitfenster fuer Vorher/Nachher-Messung?",
                    "Wer darf Batch-/SQL-/AOS-Aenderungen fachlich freigeben?",
                    "Welche Rollback-Konfiguration muss vor Umsetzung gesichert werden?",
                ],
                "safeBoundary": "No production execution from dashboard; generate proposal, validate in TEST, then CAB/GxP approval.",
            }
        )
    return questions


def generate_ai_ki_extensions(evidence: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    return {
        "hypothesisRanking": hypothesis_ranking(findings),
        "counterfactuals": counterfactuals(findings),
        "causalNarrative": causal_narrative(findings),
        "llmContextPack": llm_context_pack(findings),
        "evidenceChunks": evidence_chunks(findings),
        "confidenceCalibration": confidence_calibration(findings),
        "batchRescheduleSimulator": batch_reschedule_simulator(evidence, findings),
        "rootCauseBridge": root_cause_bridge(evidence, findings),
        "nextBestEvidence": next_best_evidence(findings, evidence),
        "changeRoiPrioritizer": change_roi_prioritizer(findings),
        "adminCopilotQuestions": admin_copilot_questions(findings),
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
