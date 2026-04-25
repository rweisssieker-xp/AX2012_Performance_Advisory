import argparse
from _export_feature import write_output
from axpa_core import load_evidence, stable_id

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ev = load_evidence(args.evidence)
rows = []
for source in ("batch_jobs", "trace_parser", "sql_top_queries"):
    for row in ev.tables[source]:
        text = " ".join(str(v) for v in row.values()).upper()
        if "CUSTOM" in text or "CUS" in text:
            rows.append({"id": stable_id([source, text[:80]]), "source": source, "risk": "high", "evidence": text[:240], "owner": "AX Development"})
write_output(args.output, rows)
