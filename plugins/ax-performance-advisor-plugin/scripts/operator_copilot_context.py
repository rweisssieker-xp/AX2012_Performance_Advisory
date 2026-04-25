import argparse
from _export_feature import write_output
from axpa_core import operator_copilot_context
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, operator_copilot_context(args.evidence))
