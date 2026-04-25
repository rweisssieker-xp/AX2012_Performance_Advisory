---
name: temporal-hotspot-analysis
description: Analyze AX workload pressure by hour, day, business calendar, and maintenance window.
---

# Temporal Hotspot Analysis

Use this skill for incident windows, night jobs, close processes, and workload calendars.

## Workflow

1. Run `scripts/temporal_hotspot_map.py`.
2. Run `scripts/map_workload_calendar.py`.
3. Correlate hot windows with batch, SQL waits, query families, and business events.

