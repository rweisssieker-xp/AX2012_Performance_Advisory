from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from axpa_core import write_json


def check(config: str | Path) -> dict:
    cfg = json.loads(Path(config).read_text(encoding="utf-8"))
    result = {"mode": cfg.get("mode", "environment"), "systems": {}}
    for system, names in cfg.get("requiredForPush", {}).items():
        present = [name for name in names if os.getenv(name)]
        missing = [name for name in names if not os.getenv(name)]
        result["systems"][system] = {"ready": not missing, "present": present, "missing": missing}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AXPA secret/config readiness without printing secret values.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = check(args.config)
    write_json(args.output, payload)
    print(f"Wrote secret readiness to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
