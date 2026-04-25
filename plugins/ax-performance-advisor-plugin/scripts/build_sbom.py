from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a lightweight AXPA SBOM/file inventory.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part in {"out", "evidence", "__pycache__"} for part in path.relative_to(root).parts):
            files.append({
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
                "type": path.suffix.lower() or "none"
            })
    payload = {"format": "AXPA-SBOM-0.1", "componentCount": len(files), "components": files}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote SBOM to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
