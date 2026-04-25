import argparse
from _export_feature import write_output
from axpa_core import regression_unit_tests
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, regression_unit_tests(args.evidence))
