---
name: traceparser-dynamicsperf-analysis
description: Analyze Trace Parser and DynamicsPerf evidence, including long-running X++ code, SQL queries, call counts, call trees, and Query-to-X++ links.
---

# Trace Parser And DynamicsPerf Analysis

Use this skill when Trace Parser or DynamicsPerf exports are available.

## Workflow

1. Normalize exports with `import_trace_parser_export.py` or `import_dynamicsperf_export.py`.
2. Run `link_query_to_xpp.py`.
3. Review custom classes, methods, high SQL cost, and call-count patterns.
4. Route custom-code findings to the owning development or vendor team.

