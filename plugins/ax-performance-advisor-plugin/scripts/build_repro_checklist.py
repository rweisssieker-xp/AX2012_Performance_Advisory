import argparse
from pathlib import Path
from axpa_core import load_evidence

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
lines = ["# Test-vs-Prod Repro Checklist", "", "- Match AX build/model version.", "- Restore comparable data volume for hot tables.", "- Align statistics age and sample rates.", "- Align batch schedule and AOS assignment.", "- Reproduce with same business calendar window.", ""]
for row in ev.tables["environment_drift"][:20]:
    lines.append(f"- Drift: {row}")
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {args.output}")
