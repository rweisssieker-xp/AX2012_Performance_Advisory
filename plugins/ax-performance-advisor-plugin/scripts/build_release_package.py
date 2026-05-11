from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "dist",
    "evidence",
    "out",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
EXCLUDE_NAMES = {
    ".coverage",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def include_file(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    if not path.is_file():
        return False
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    if path.name in EXCLUDE_NAMES:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build signed/checksummed AXPA plugin release package.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", default="")
    parser.add_argument("--prefix", default="ax-performance-advisor-plugin")
    args = parser.parse_args()
    root = Path(args.root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if not include_file(root, path):
                continue
            rel = path.relative_to(root).as_posix()
            zip_rel = f"{args.prefix}/{rel}" if args.prefix else rel
            z.write(path, zip_rel)
            files.append({"path": zip_rel, "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {
        "package": str(output),
        "version": args.version,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sha256": sha(output),
        "fileCount": len(files),
        "excludedDirectories": sorted(EXCLUDE_DIRS),
        "files": files,
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote release package {output}")
    print(f"Wrote release manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
