import argparse
from pathlib import Path

from axpa_core import analyze_evidence, export_evidence_pack, now_iso


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a CAB/change-control package from AXPA findings.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    findings = analyze_evidence(args.evidence)
    high = [item for item in findings if item["severity"] in {"critical", "high"}]
    lines = [
        "# AX Performance Advisor CAB Package",
        "",
        f"Generated: {now_iso()}",
        f"Evidence: {args.evidence}",
        "",
        "## Change Summary",
        "",
        f"- Findings included: {len(findings)}",
        f"- Critical/high findings: {len(high)}",
        "- Change type: Advisory proposal requiring approval",
        "- Implementation authority: Customer CAB / validated change process",
        "",
        "## Proposed Scope",
        "",
    ]
    for item in high[:10]:
        lines.extend([
            f"### {item['id']} - {item['title']}",
            "",
            f"- Severity: {item['severity']}",
            f"- Owner: {item['axContext'].get('technicalOwner', '')}",
            f"- Business owner: {item['axContext'].get('businessOwner', '')}",
            f"- Recommendation: {item['recommendation'].get('summary', '')}",
            f"- Risk if implemented: {item['changeReadiness']}",
            f"- Validation: {item['validation'].get('successMetric', '')}",
            f"- Rollback: {item['validation'].get('rollback', '')}",
            "",
        ])
    (output / "cab-package.md").write_text("\n".join(lines), encoding="utf-8")
    pack = export_evidence_pack(args.evidence, output / "cab-evidence-pack.zip")
    print(f"Wrote CAB package to {output / 'cab-package.md'} and {pack}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
