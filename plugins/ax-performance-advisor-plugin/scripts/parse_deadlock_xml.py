import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_deadlock(path: Path) -> list[dict[str, str]]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    rows = []
    for process in root.findall(".//process"):
        rows.append({
            "source_file": str(path),
            "process_id": process.attrib.get("id", ""),
            "spid": process.attrib.get("spid", ""),
            "waitresource": process.attrib.get("waitresource", ""),
            "waittime_ms": process.attrib.get("waittime", ""),
            "hostname": process.attrib.get("hostname", ""),
            "clientapp": process.attrib.get("clientapp", ""),
            "loginname": process.attrib.get("loginname", ""),
            "transactionname": process.attrib.get("transactionname", ""),
            "inputbuf": "".join(process.findtext("inputbuf", default="").split()),
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse SQL Server deadlock XML files into deadlock_processes.csv.")
    parser.add_argument("--input", required=True, help="Deadlock XML file or directory.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_path = Path(args.input)
    files = list(input_path.glob("*.xml")) if input_path.is_dir() else [input_path]
    rows = []
    for file in files:
        rows.extend(parse_deadlock(file))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_file", "process_id", "spid", "waitresource", "waittime_ms", "hostname", "clientapp", "loginname", "transactionname", "inputbuf"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} deadlock process rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
