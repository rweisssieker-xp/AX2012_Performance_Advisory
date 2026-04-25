import argparse
from _export_feature import write_output
from axpa_core import plan_regression_watcher
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, plan_regression_watcher(args.evidence))
