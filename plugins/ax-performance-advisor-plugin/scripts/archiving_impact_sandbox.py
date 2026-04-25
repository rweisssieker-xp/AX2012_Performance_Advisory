import argparse
from _export_feature import write_output
from axpa_core import archiving_impact_sandbox
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); parser.add_argument("--archive-percent",type=float,default=50.0); args=parser.parse_args()
write_output(args.output, archiving_impact_sandbox(args.evidence,args.archive_percent))
