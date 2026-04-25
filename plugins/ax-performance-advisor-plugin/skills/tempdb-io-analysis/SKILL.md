---
name: tempdb-io-analysis
description: Analyze TempDB pressure, file latency, PAGEIOLATCH/WRITELOG waits, spills, and storage-related AX performance risk.
---

# TempDB And I/O Analysis

Use this skill for TempDB, file latency, PAGEIOLATCH, WRITELOG, spills, and storage pressure.

## Workflow

1. Review `tempdb_usage.csv`, `file_latency.csv`, waits, and plan spill warnings.
2. Correlate with batch/report windows and high-read query families.
3. Recommend validation of file layout, storage latency, query spills, and maintenance overlap.

## Related Scripts

- `analyze_evidence.py`
- `parse_plan_xml.py`
- `forecast_capacity_exhaustion.py`

