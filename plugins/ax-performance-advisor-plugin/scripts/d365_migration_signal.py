import argparse
from _export_feature import write_output
from axpa_core import d365_migration_signal
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, d365_migration_signal(args.evidence))
