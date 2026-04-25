import argparse
from _export_feature import write_output
from axpa_core import load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
jobs = sorted(ev.tables["batch_jobs"], key=lambda r: float(r.get("duration_seconds") or 0), reverse=True)
rows = []
cursor = 0
for job in jobs:
    duration = int(float(job.get("duration_seconds") or 0))
    rows.append({"job": job.get("job_name"), "recommendedStartMinute": cursor, "durationSeconds": duration, "rationale": "Longest jobs scheduled first; validate business constraints."})
    cursor += max(1, duration // 60)
write_output(args.output, rows)
