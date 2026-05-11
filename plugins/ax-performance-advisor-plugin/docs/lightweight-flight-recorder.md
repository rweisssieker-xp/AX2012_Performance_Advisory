# AX Lightweight Flight Recorder

The Lightweight Flight Recorder localizes slow AX frontend situations without installing Trace Parser and without adding load to AX clients.

## Principle

It uses short, read-only server-side snapshots:

- SQL active requests and top queries
- AX live blocking/session evidence
- wait and blocking rows
- user, host, AOS and session identifiers where available
- Query Store evidence when already collected

No AX client component is required. No SQL Profiler trace is required.

The live collector uses `collect_sql_live_snapshot.ps1`, not the full SQL inventory collector. It avoids index fragmentation scans, statistics scans, missing-index sweeps across the whole database, and other heavier inventory work.

## Commands

Live read-only server-side capture:

```powershell
powershell scripts/collect_lightweight_flight_recorder.ps1 `
  -ConnectionString "<readonly-sql-connection>" `
  -OutputDirectory out\flight-live `
  -AxDatabaseName MicrosoftDynamicsGBLAX `
  -AosComputerName BRAS3333 `
  -IntervalSeconds 5 `
  -Samples 12 `
  -IncludeAosCounters `
  -IncludeEvents `
  -IncludeQueryStore
```

Analyze an existing evidence folder:

```powershell
python scripts/flight_recorder.py analyze --evidence evidence\bras3333-current --output out\bras3333-lightweight-flight-recorder.json
```

Record repeated copies of an existing evidence folder:

```powershell
python scripts/flight_recorder.py record --source-evidence evidence\bras3333-current --output-dir out\flight-snapshots --interval-seconds 5 --samples 12
```

## What It Detects

- wide inventory frontend queries
- `INVENTSUM` / `INVENTDIM` all-dimension stock availability patterns
- high logical reads, CPU and elapsed time
- blocking relationships
- user/host/session pressure
- likely business process from SQL pattern
- AOS counter pressure when `aos_counters.csv` is present
- AX event-log signals when `ax_events.csv` is present
- Query Store hotspots when Query Store evidence is present
- complaint matches by user, host and text
- known-pattern seeds for future operator feedback

## Limitation

Without Trace Parser or DynamicsPerf, form and X++ method attribution is inferred from SQL/session patterns. This is usually enough for broad inventory and blocking incidents, but not enough for exact call-tree proof.
