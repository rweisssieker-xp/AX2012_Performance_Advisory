import argparse
from axpa_core import approval_workflow
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
print(f"Wrote {approval_workflow(args.evidence,args.output)}")
