import argparse
import shutil
import time
from datetime import datetime
from pathlib import Path


parser = argparse.ArgumentParser(description="Record lightweight evidence snapshots from an existing evidence source directory.")
parser.add_argument("--source-evidence", required=True)
parser.add_argument("--output-dir", required=True)
parser.add_argument("--interval-seconds", type=int, default=300)
parser.add_argument("--samples", type=int, default=1)
args = parser.parse_args()

out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
for _ in range(args.samples):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = out / stamp
    shutil.copytree(args.source_evidence, target, dirs_exist_ok=True)
    print(f"Recorded snapshot {target}")
    if _ < args.samples - 1:
        time.sleep(args.interval_seconds)
