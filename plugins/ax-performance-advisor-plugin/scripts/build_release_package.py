from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


EXCLUDE = {"out", "evidence", "__pycache__"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build signed/checksummed AXPA plugin release package.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part in EXCLUDE for part in path.relative_to(root).parts):
                continue
            rel = path.relative_to(root).as_posix()
            z.write(path, rel)
            files.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {"package": str(output), "sha256": sha(output), "fileCount": len(files), "files": files}
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote release package {output}")
    print(f"Wrote release manifest {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
