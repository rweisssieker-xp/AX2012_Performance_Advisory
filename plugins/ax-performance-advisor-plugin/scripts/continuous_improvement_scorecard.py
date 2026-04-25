import argparse
from _export_feature import write_output
from axpa_core import analyze_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
findings = analyze_evidence(args.evidence)
write_output(args.output, {"openFindings": len(findings), "highCritical": sum(1 for f in findings if f["severity"] in {"high","critical"}), "validatedClosed": 0, "regressions": sum(1 for f in findings if f["recommendation"].get("playbook") == "deployment-regression")})
