import argparse
from axpa_core import anonymized_pattern_export
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
print(f"Wrote {anonymized_pattern_export(args.evidence,args.output)}")
