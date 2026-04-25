from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run_once(config: dict, log_path: Path) -> dict:
    evidence = config["evidence"]
    output = config["output"]
    scripts = Path(__file__).resolve().parent
    commands = [
        [sys.executable, str(scripts / "generate_dashboard.py"), "--evidence", evidence, "--output", str(Path(output) / "dashboard.html")],
        [sys.executable, str(scripts / "enterprise_observability.py"), "--evidence", evidence, "--output-dir", str(Path(output) / "enterprise-observability"), "--estate", evidence],
    ]
    results = []
    for cmd in commands:
        completed = subprocess.run(cmd, text=True, capture_output=True, timeout=int(config.get("commandTimeoutSeconds", 300)))
        results.append({"cmd": cmd, "returncode": completed.returncode, "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]})
    event = {"timestamp": datetime.now(timezone.utc).isoformat(), "results": results}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional AXPA local agent. Not required for plugin use.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    log_path = Path(config.get("logPath", "out/optional-agent.log"))
    if args.once:
        event = run_once(config, log_path)
        print(json.dumps(event, indent=2))
        return 0
    interval = int(config.get("intervalSeconds", 3600))
    while True:
        run_once(config, log_path)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
