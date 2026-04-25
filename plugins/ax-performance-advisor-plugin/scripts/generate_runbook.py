import argparse
from _export_feature import write_output
from axpa_core import runbook_generator
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, runbook_generator(args.evidence))
