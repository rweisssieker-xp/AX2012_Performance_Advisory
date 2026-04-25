import argparse
from _export_feature import write_output
from axpa_core import analyze_evidence

KNOWN = [
    {"pattern": "stale-statistics", "issue": "Stale statistics causing bad cardinality estimates", "fixPath": "Targeted statistics update and post-change plan validation"},
    {"pattern": "parameter-sensitive-plan", "issue": "Parameter-sensitive AX query plan", "fixPath": "Compare plans and validate query/statistics strategy"},
    {"pattern": "data-growth", "issue": "Data lifecycle pressure", "fixPath": "Archive/retention assessment"},
]
parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
rows = []
for finding in analyze_evidence(args.evidence):
    playbook = finding["recommendation"].get("playbook", "")
    for known in KNOWN:
        if known["pattern"] == playbook:
            rows.append({"findingId": finding["id"], **known})
write_output(args.output, rows)
