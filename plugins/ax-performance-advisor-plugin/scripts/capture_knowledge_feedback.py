import argparse
from axpa_core import knowledge_feedback
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); parser.add_argument("--resolution",default="unresolved"); args=parser.parse_args()
print(f"Wrote {knowledge_feedback(args.evidence,args.output,args.resolution)}")
