# AX Batch Collision Analysis

This feature performs a read-only collision analysis from AX batch evidence.

## Inputs

- `batch_tasks.csv`: task id, job id, caption, batch group, company, status, start time, end time, duration.
- `batch_jobs.csv`: fallback source when task-level rows are unavailable.
- `ax_live_blocking.csv`: optional correlation signal for live blocked AX workers.

## Real Checks

- Pairwise overlap detection for batch tasks with real start/end timestamps.
- Batch-group collision ranking by total overlap seconds and max overlap.
- Peak concurrency calculation from interval start/end events.
- Short-runner storm detection for many 0-30 second tasks starting in the same minute.
- Long-runner ranking for tasks exceeding 10 minutes.
- Finding generation for collision hotspots, group collisions, and short-runner storms.
- Dashboard tab `Batch Collisions`.
- SQLite trend tables `batch_run_metrics` and `batch_group_collisions`.

## Interpretation

High overlap does not automatically mean a batch is wrong. It means the schedule needs
review against SQL waits, live blocking, AOS capacity, business priority, and recurrence.
Recommended changes remain advisory and should be tested in TEST before production.

## Validation

After changing a batch schedule, compare the next equivalent run:

- peak concurrency,
- collision count,
- group overlap seconds,
- affected batch runtime,
- SQL wait delta,
- live blocking rows.
