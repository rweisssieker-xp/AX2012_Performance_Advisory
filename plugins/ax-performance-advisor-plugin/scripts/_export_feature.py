import argparse
import csv
import json
from pathlib import Path


def write_output(output: str, payload):
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".csv" and isinstance(payload, list):
        with path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = sorted({key for row in payload for key in row.keys()}) if payload else ["empty"]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(payload)
    elif isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
