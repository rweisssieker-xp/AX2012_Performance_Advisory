from __future__ import annotations

from pathlib import Path
from typing import Any


def _infer_form(tables: list[str]) -> tuple[str, int]:
    upper = {t.upper() for t in tables}
    if "INVENTSUM" in upper or "INVENTDIM" in upper:
        return "InventOnHand", 82
    if "GENERALJOURNALACCOUNTENTRY" in upper:
        return "Ledger posting", 70
    if any(t.startswith("WHS") for t in upper):
        return "Warehouse management form", 65
    if any(t.startswith("SALESTABLE") or t.startswith("SALESLINE") for t in upper):
        return "Sales order form", 60
    return "unknown", 0


def generate_attribution_engine(evidence: str | Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    root = Path(evidence)
    deep_files = ["trace_parser.csv", "dynamicsperf.csv", "ax_model_mapping.csv"]
    present = [name for name in deep_files if (root / name).exists() and (root / name).stat().st_size > 3]
    missing = [name for name in deep_files if name not in present]
    items: list[dict[str, Any]] = []
    for finding in findings[:100]:
        ax = finding.get("axContext") or {}
        sql = finding.get("sqlContext") or {}
        tables = [str(t) for t in (ax.get("tables") or sql.get("objects") or []) if str(t)]
        form, score = _infer_form(tables)
        confidence = "direct" if present else "strong-inference" if score >= 70 else "weak-inference" if score else "missing"
        items.append(
            {
                "findingId": finding.get("id", ""),
                "title": finding.get("title", ""),
                "observed": {
                    "tables": tables,
                    "queryHash": sql.get("queryHash") or sql.get("query_hash") or "",
                    "module": ax.get("module", "Unknown"),
                },
                "inferred": {
                    "form": form,
                    "businessProcess": ax.get("module", "Unknown"),
                    "score": score,
                },
                "confidence": confidence,
                "presentProof": present,
                "missingProof": missing,
                "nextCollector": "Collect Trace Parser, DynamicsPerf or AX model mapping during the same slow window." if missing else "Review direct attribution evidence.",
            }
        )
    return {"itemCount": len(items), "deepModeReady": bool(present), "presentSources": present, "missingSources": missing, "items": items}
