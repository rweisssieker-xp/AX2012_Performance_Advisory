import argparse
from _export_feature import write_output
from axpa_core import recommendation_scenarios
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, recommendation_scenarios(args.evidence))
