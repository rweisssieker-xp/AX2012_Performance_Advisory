from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from axpa_core import analyze_evidence, write_json


def _signature(f: dict[str, Any]) -> str:
    return "|".join([
        f.get("recommendation", {}).get("playbook", "review"),
        f.get("axContext", {}).get("module", "Unknown"),
        ",".join(f.get("axContext", {}).get("tables", [])[:3]),
    ])


def update_recommendation_memory(evidence: str | Path, db: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    dbp = Path(db)
    dbp.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dbp) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS memory (signature TEXT PRIMARY KEY, seen INTEGER, accepted INTEGER, rejected INTEGER, last_title TEXT)")
        for f in findings:
            sig = _signature(f)
            conn.execute(
                "INSERT INTO memory(signature, seen, accepted, rejected, last_title) VALUES (?,1,0,0,?) ON CONFLICT(signature) DO UPDATE SET seen=seen+1,last_title=excluded.last_title",
                (sig, f["title"]),
            )
        conn.commit()
        rows = conn.execute("SELECT signature, seen, accepted, rejected, last_title FROM memory ORDER BY seen DESC LIMIT 50").fetchall()
    return {"db": str(dbp), "entries": [{"signature": r[0], "seen": r[1], "accepted": r[2], "rejected": r[3], "lastTitle": r[4]} for r in rows]}


def similarity_search(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in findings[:40]:
        sig = set(_signature(f).lower().split("|"))
        sims = []
        for other in findings:
            if other["id"] == f["id"]:
                continue
            osig = set(_signature(other).lower().split("|"))
            score = len(sig & osig)
            if score:
                sims.append({"findingId": other["id"], "score": score, "title": other["title"]})
        rows.append({"findingId": f["id"], "similar": sorted(sims, key=lambda x: x["score"], reverse=True)[:5]})
    return rows


def acceptance_simulation(findings: list[dict[str, Any]]) -> dict[str, Any]:
    high = [f for f in findings if f.get("severity") in {"critical", "high"}]
    medium = [f for f in findings if f.get("severity") == "medium"]
    return {
        "acceptAllHighRisk": {"items": len(high), "governanceLoad": "high", "expectedRiskReduction": "requires validation"},
        "acceptLowRiskMaintenanceOnly": {"items": len(medium), "governanceLoad": "medium", "expectedRiskReduction": "gradual"},
        "deferAll": {"items": len(findings), "governanceLoad": "low-now/high-later", "expectedRiskReduction": "none"},
    }


def executive_narrative_variants(findings: list[dict[str, Any]]) -> dict[str, str]:
    sev = Counter(f.get("severity") for f in findings)
    playbooks = Counter(f.get("recommendation", {}).get("playbook", "review") for f in findings)
    top = ", ".join(p for p, _ in playbooks.most_common(3))
    return {
        "cio": f"AXPA detected {len(findings)} findings, including {sev['high'] + sev['critical']} high/critical risks. Main themes: {top}. Decision needed: approve TEST validation and controlled remediation.",
        "dba": f"Prioritize SQL evidence around {top}. Validate wait/query/statistics changes with before/after Query Store and AXPA evidence.",
        "qaGxp": "All high-risk actions require evidence pack, test objective, expected result, actual result, deviation handling, rollback, and approval reference.",
        "processOwner": f"Performance risk is concentrated in {top}. Confirm business windows and acceptable validation timing.",
    }


def anomaly_explanation(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in findings:
        if f.get("severity") in {"critical", "high"}:
            rows.append({
                "findingId": f["id"],
                "anomaly": f["title"],
                "plainExplanation": f.get("likelyCause", "High-risk technical signal detected."),
                "whatWouldConfirm": f.get("validation", {}).get("successMetric", "Comparable before/after evidence."),
                "whatCouldDisprove": "If comparable post-change or repeated evidence shows no recurrence under same workload.",
            })
    return rows[:30]


def action_confidence_tuning(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for f in findings:
        evidence_count = len(f.get("evidence", []))
        risk = f.get("changeReadiness", {})
        score = min(100, evidence_count * 20 + (20 if f.get("confidence") == "high" else 10) - (10 if risk.get("technicalRisk") == "high" else 0))
        rows.append({"findingId": f["id"], "actionConfidence": max(0, score), "evidenceCount": evidence_count, "declaredConfidence": f.get("confidence"), "riskPenalty": risk.get("technicalRisk", "medium")})
    return sorted(rows, key=lambda x: x["actionConfidence"], reverse=True)


def generate_learning_extensions(evidence: str | Path, output_dir: str | Path) -> dict[str, Any]:
    findings = analyze_evidence(evidence)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    return {
        "recommendationMemory": update_recommendation_memory(evidence, out / "recommendation-memory.sqlite"),
        "similaritySearch": similarity_search(findings),
        "acceptanceSimulation": acceptance_simulation(findings),
        "executiveNarrativeVariants": executive_narrative_variants(findings),
        "anomalyExplanation": anomaly_explanation(findings),
        "actionConfidenceTuning": action_confidence_tuning(findings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXPA learning and AI decision extensions.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    payload = generate_learning_extensions(args.evidence, args.output_dir)
    write_json(Path(args.output_dir) / "learning-extensions.json", payload)
    print(f"Wrote learning extensions to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
