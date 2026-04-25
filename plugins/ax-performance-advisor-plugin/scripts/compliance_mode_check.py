import argparse
from _export_feature import write_output
from axpa_core import compliance_mode_check
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, compliance_mode_check(args.evidence))
