import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


NS = {"sp": "http://schemas.microsoft.com/sqlserver/2004/07/showplan"}


def attr_float(node, name: str) -> float:
    try:
        return float(node.attrib.get(name, "0"))
    except ValueError:
        return 0.0


def parse_plan(path: Path) -> list[dict[str, str]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows = []
    for relop in root.findall(".//sp:RelOp", NS):
        physical = relop.attrib.get("PhysicalOp", "")
        logical = relop.attrib.get("LogicalOp", "")
        est_rows = relop.attrib.get("EstimateRows", "")
        est_cost = relop.attrib.get("EstimatedTotalSubtreeCost", "")
        warnings = []
        if relop.find(".//sp:SpillToTempDb", NS) is not None:
            warnings.append("spill-to-tempdb")
        if relop.find(".//sp:MissingIndexes", NS) is not None:
            warnings.append("missing-index")
        rows.append({
            "source_file": str(path),
            "physical_op": physical,
            "logical_op": logical,
            "estimate_rows": est_rows,
            "estimated_cost": est_cost,
            "warnings": ";".join(warnings),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse SQL Server execution plan XML into plan_operators.csv.")
    parser.add_argument("--input", required=True, help="Plan XML file or directory.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    files = list(input_path.glob("*.sqlplan")) + list(input_path.glob("*.xml")) if input_path.is_dir() else [input_path]
    rows = []
    for file in files:
        rows.extend(parse_plan(file))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_file", "physical_op", "logical_op", "estimate_rows", "estimated_cost", "warnings"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} plan operator rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
