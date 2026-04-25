import argparse
from pathlib import Path

from axpa_core import analyze_evidence


def safe_name(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text)[:80]


def validation_sql(finding: dict) -> str:
    objects = finding.get("sqlContext", {}).get("objects", []) or finding.get("axContext", {}).get("tables", [])
    obj = objects[0] if objects else ""
    return f"""-- Validation script for {finding['id']} - {finding['title']}
-- Read-only. Review before execution.
SELECT GETDATE() AS validation_time;
SELECT '{finding['id']}' AS finding_id, '{finding['severity']}' AS severity, '{finding['classification']}' AS classification;
-- Evidence metric: {finding['evidence'][0].get('metric')} observed value {finding['evidence'][0].get('value')}
{f"SELECT TOP (20) * FROM {obj} WITH (NOLOCK);" if obj.startswith("dbo.") else "-- No concrete SQL object available for this finding."}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate read-only SQL validation scripts per finding.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--minimum-severity", default="high", choices=["informational", "low", "medium", "high", "critical"])
    args = parser.parse_args()
    rank = {"informational": 1, "low": 2, "medium": 3, "high": 4, "critical": 5}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    for finding in analyze_evidence(args.evidence):
        if rank[finding["severity"]] < rank[args.minimum_severity]:
            continue
        (out / f"{finding['id']}-{safe_name(finding['title'])}.sql").write_text(validation_sql(finding), encoding="utf-8")
        count += 1
    print(f"Wrote {count} validation scripts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
