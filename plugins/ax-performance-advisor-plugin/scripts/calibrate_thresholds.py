import argparse
from _export_feature import write_output
from axpa_core import load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
durations = sorted(float(r.get("avg_duration_ms") or 0) for r in ev.tables["sql_top_queries"])
reads = sorted(float(r.get("total_logical_reads") or 0) for r in ev.tables["sql_top_queries"])
def p(values, pct):
    return values[int((len(values)-1) * pct)] if values else 0
write_output(args.output, {"thresholds": {"queryAvgDurationMsP95": p(durations, .95), "logicalReadsP95": p(reads, .95)}})
