import argparse
from _export_feature import write_output
from axpa_core import load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
rows = []
for row in ev.tables["table_growth"]:
    size = float(row.get("size_mb") or 0)
    closed = float(row.get("closed_record_pct") or 0)
    reclaim = round(size * closed / 100, 1)
    rows.append({"table": row.get("object_name"), "sizeMb": size, "closedRecordPct": closed, "estimatedReclaimableMb": reclaim, "recommendation": "Assess archive/cleanup with legal and reporting owners."})
write_output(args.output, rows)
