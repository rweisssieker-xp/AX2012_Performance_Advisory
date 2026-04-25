import argparse
from _export_feature import write_output
from axpa_core import validation_orchestrator
parser=argparse.ArgumentParser(); parser.add_argument("--before",required=True); parser.add_argument("--after",required=True); parser.add_argument("--output-dir",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, validation_orchestrator(args.before,args.after,args.output_dir))
