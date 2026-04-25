import argparse
from axpa_core import self_healing_rule_update
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
print(f"Wrote {self_healing_rule_update(args.evidence,args.output)}")
