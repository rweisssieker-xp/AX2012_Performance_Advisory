from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _hour(value: str) -> str:
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).strftime("%H:00")
        except ValueError:
            continue
    return "unknown"


def _target_hour(hourly: Counter[str], source: str) -> str:
    candidates = ["21:00", "22:00", "23:00", "00:00", "01:00", "02:00"]
    ranked = sorted(candidates, key=lambda h: (hourly.get(h, 0), 1 if h == source else 0, h))
    return ranked[0]


def generate_batch_control_tower(evidence: str | Path) -> dict[str, Any]:
    root = Path(evidence)
    rows = _read_csv(root / "batch_tasks.csv")
    hourly: Counter[str] = Counter()
    group_by_hour: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        hour = _hour(str(row.get("start_time") or ""))
        group = str(row.get("batch_group") or "unknown")
        hourly[hour] += 1
        group_by_hour[hour][group] += 1
        key = (hour, group)
        if len(examples[key]) < 5:
            examples[key].append({"taskId": row.get("task_id", ""), "caption": row.get("caption", ""), "durationSeconds": row.get("duration_seconds", "")})

    move_candidates: list[dict[str, Any]] = []
    for hour, count in hourly.most_common(12):
        if hour == "unknown" or count < 2:
            continue
        group, group_count = group_by_hour[hour].most_common(1)[0]
        target = _target_hour(hourly, hour)
        reduction = round(group_count * 100 / max(1, count))
        move_candidates.append(
            {
                "sourceHour": hour,
                "targetHour": target,
                "batchGroup": group,
                "taskCount": count,
                "moveTaskCount": group_count,
                "expectedOverlapReductionPercent": reduction,
                "exampleTasks": examples[(hour, group)],
                "dependencyRisk": f"Check jobs that consume output from {group} after {target}.",
                "implementationHint": f"In TEST, move only recurrence/start time for group {group} from {hour} to {target}.",
                "validation": "Compare source/target peak concurrency, duration p95, blocking rows, Query Store reads and business finish time.",
                "rollback": f"Restore original {hour} schedule for group {group} if SLA or downstream completion regresses.",
            }
        )

    groups = Counter(str(r.get("batch_group") or "unknown") for r in rows)
    return {
        "taskCount": len(rows),
        "hourlyLoad": [{"hour": k, "tasks": v} for k, v in sorted(hourly.items())],
        "groupLoad": [{"group": k, "tasks": v} for k, v in groups.most_common()],
        "moveCandidates": move_candidates,
        "slaContracts": [{"batchGroup": group, "targetFinish": "before business start", "owner": "AX Operations", "escalation": "IT Operations"} for group, _ in groups.most_common(10)],
        "dependencyGraph": {"nodes": sorted(groups), "edges": []},
        "aosAffinity": {"status": "needs-aos-evidence", "recommendation": "Collect AOS/session counters during batch peaks for placement advice."},
    }
