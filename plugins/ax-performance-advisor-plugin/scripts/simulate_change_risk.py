import argparse
from _export_feature import write_output

parser = argparse.ArgumentParser()
parser.add_argument("--change-type", required=True, choices=["index", "batch-move", "statistics", "archive"])
parser.add_argument("--object", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
profiles = {
    "index": {"benefit": "medium-high", "risk": "medium", "validation": "reads, CPU, writes, blocking", "rollback": "drop index after approval"},
    "batch-move": {"benefit": "medium", "risk": "low", "validation": "runtime, overlap, SLA buffer", "rollback": "restore schedule"},
    "statistics": {"benefit": "medium", "risk": "low", "validation": "plan stability, reads, duration", "rollback": "normally no rollback; monitor plan regression"},
    "archive": {"benefit": "high", "risk": "high", "validation": "row count, reporting, legal retention", "rollback": "restore archived records per approved plan"},
}
write_output(args.output, {"object": args.object, "changeType": args.change_type, **profiles[args.change_type]})
