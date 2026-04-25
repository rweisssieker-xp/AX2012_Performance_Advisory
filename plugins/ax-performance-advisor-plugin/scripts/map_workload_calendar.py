import argparse
from _export_feature import write_output
from axpa_core import workload_calendar_map
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, workload_calendar_map(args.evidence))
