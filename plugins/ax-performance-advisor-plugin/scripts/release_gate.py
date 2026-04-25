import argparse
from _export_feature import write_output
from axpa_core import release_gate
parser=argparse.ArgumentParser(); parser.add_argument("--before",required=True); parser.add_argument("--after",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, release_gate(args.before,args.after))
