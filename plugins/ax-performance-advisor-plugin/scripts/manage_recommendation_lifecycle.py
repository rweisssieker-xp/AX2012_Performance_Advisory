from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


VALID_STATES = {"proposed", "accepted", "needs_evidence", "in_test", "ready_for_test", "approved", "implemented", "verified", "deferred", "rejected"}
TRANSITIONS = {
    "proposed": {"accepted", "deferred", "rejected"},
    "accepted": {"needs_evidence", "in_test", "approved", "deferred", "rejected"},
    "needs_evidence": {"in_test", "deferred", "rejected"},
    "in_test": {"approved", "rejected", "deferred"},
    "ready_for_test": {"in_test", "deferred", "rejected"},
    "approved": {"implemented", "deferred"},
    "implemented": {"verified", "rejected"},
    "verified": set(),
    "deferred": {"accepted", "rejected"},
    "rejected": set(),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_state(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"version": 1, "items": {}, "audit": []}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage persistent AXPA recommendation lifecycle states.")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--finding-id")
    parser.add_argument("--state", choices=sorted(VALID_STATES))
    parser.add_argument("--actor", default="operator")
    parser.add_argument("--note", default="")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    path = Path(args.state_file)
    state = load_state(path)
    state.setdefault("items", {})
    state.setdefault("audit", [])

    if args.list:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0
    if not args.finding_id or not args.state:
        raise SystemExit("--finding-id and --state are required unless --list is used.")

    current = state["items"].get(args.finding_id, {}).get("state", "proposed")
    if not args.force and args.state != current and args.state not in TRANSITIONS.get(current, set()):
        raise SystemExit(f"Invalid transition {current} -> {args.state}. Use --force only for manual correction.")

    item = state["items"].setdefault(args.finding_id, {})
    item.update({"state": args.state, "updatedAt": now_iso(), "updatedBy": args.actor, "note": args.note})
    if args.state == "accepted":
        item["acceptedBy"] = args.actor
    if args.state == "implemented":
        item["implementedAt"] = now_iso()
    if args.state == "verified":
        item["verifiedAt"] = now_iso()
    state["audit"].append({"findingId": args.finding_id, "from": current, "to": args.state, "actor": args.actor, "note": args.note, "timestamp": now_iso(), "forced": args.force})
    save_state(path, state)
    print(json.dumps({"findingId": args.finding_id, "from": current, "to": args.state, "stateFile": str(path)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
