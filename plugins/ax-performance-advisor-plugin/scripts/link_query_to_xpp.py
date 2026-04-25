import argparse
from _export_feature import write_output
from axpa_core import query_to_xpp_trace
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, query_to_xpp_trace(args.evidence))
