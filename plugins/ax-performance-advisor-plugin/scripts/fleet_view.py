import argparse
from _export_feature import write_output
from axpa_core import fleet_view
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",nargs="+",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, fleet_view(args.evidence))
