import argparse
import hashlib
import json
from pathlib import Path


def manifest(root: Path) -> dict:
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not any(part in {"out", "evidence", "__pycache__"} for part in path.parts):
            files.append({"path": str(path.relative_to(root)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    return {"root": str(root), "fileCount": len(files), "files": files, "manifestSha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or verify plugin code integrity manifest.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    parser.add_argument("--verify")
    args = parser.parse_args()
    current = manifest(Path(args.root))
    if args.verify:
        expected = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        if expected.get("manifestSha256") != current["manifestSha256"]:
            raise SystemExit("Plugin integrity verification failed.")
        print("Plugin integrity OK")
        return 0
    if not args.output:
        raise SystemExit("--output is required unless --verify is used")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote plugin integrity manifest to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
