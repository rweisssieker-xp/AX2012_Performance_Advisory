import argparse
from _export_feature import write_output
from axpa_core import load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
jobs = ev.tables["batch_jobs"]
rows = []
for i, left in enumerate(jobs):
    for right in jobs[i + 1:]:
        overlap = left.get("aos") == right.get("aos") or left.get("batch_group") == right.get("batch_group")
        if overlap:
            rows.append({"jobA": left.get("job_name"), "jobB": right.get("job_name"), "conflict": "possible", "recommendation": "Separate AOS, batch group, or time window."})
write_output(args.output, rows)
