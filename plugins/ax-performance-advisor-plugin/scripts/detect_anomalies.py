import argparse
from _export_feature import write_output
from axpa_core import anomaly_detection
parser=argparse.ArgumentParser(); parser.add_argument("--evidence",required=True); parser.add_argument("--trend-db"); parser.add_argument("--output",required=True); args=parser.parse_args()
write_output(args.output, anomaly_detection(args.evidence, args.trend_db))
