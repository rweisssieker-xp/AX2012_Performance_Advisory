import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


SENSITIVE_COLUMNS = {"login_name", "loginname", "user_id", "hostname", "client_computer", "clientapp", "statement_text", "query_sql_text", "inputbuf"}


def mask_value(value: str) -> str:
    if value is None or value == "":
        return ""
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    return f"masked-{digest}"


def mask_csv(src: Path, dst: Path) -> None:
    with src.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append({key: mask_value(val) if key.lower() in SENSITIVE_COLUMNS else val for key, val in row.items()})
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=reader.fieldnames or [])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a masked copy of an evidence directory.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    src_root = Path(args.input)
    dst_root = Path(args.output)
    for src in src_root.rglob("*"):
        if not src.is_file():
            continue
        dst = dst_root / src.relative_to(src_root)
        if src.suffix.lower() == ".csv":
            mask_csv(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
    print(f"Wrote masked evidence to {dst_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
