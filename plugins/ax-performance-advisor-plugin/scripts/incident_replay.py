import argparse
from pathlib import Path

from axpa_core import analyze_evidence, workload_fingerprint, summarize_root_causes

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
findings = analyze_evidence(args.evidence)
fingerprint = workload_fingerprint(args.evidence)
causes = summarize_root_causes(findings)
lines = ["# Incident Replay", "", f"Workload fingerprint: {fingerprint['fingerprint']} ({fingerprint['confidence']})", "", "## Timeline Narrative", ""]
for item in findings[:15]:
    lines.append(f"- {item['timeWindow'].get('start','')}: {item['severity']} - {item['title']} -> {item['recommendation']['playbook']}")
lines.extend(["", "## Root Cause Chain", ""])
for cause in causes[:8]:
    lines.append(f"- {cause['classification']} / {cause['playbook']} / {cause['module']}: {cause['count']} findings")
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {args.output}")
