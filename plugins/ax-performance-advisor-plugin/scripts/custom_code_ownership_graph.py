import argparse
from _export_feature import write_output
from axpa_core import custom_code_ownership_graph
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, custom_code_ownership_graph(args.evidence))
