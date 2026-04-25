import argparse
from _export_feature import write_output
from axpa_core import analyze_evidence, load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
changes = ev.metadata.get("changes", [])
rows = [{"change": c, "highFindings": sum(1 for f in analyze_evidence(args.evidence) if f["severity"] in {"high","critical"}), "status": "correlation-candidate"} for c in changes]
write_output(args.output, rows)
