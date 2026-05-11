# AX Frontend Machine Impact Advisor

This feature localizes AX frontend situations where one user action can slow the whole AX machine/AOS.

## Detection

The advisor scans SQL top queries and live AX blocking/session evidence for broad inventory availability patterns:

- `INVENTSUM`, `INVENTSUMUNIONDELTAPHYSICALQTY`, `WHSINVENTRESERVE`, `INVENTTRANS`
- joins to `INVENTDIM`
- many inventory dimensions such as site, warehouse, batch, location, status, serial, owner or license plate
- high logical reads, CPU or elapsed time
- live AX user/session/host context when available

## Why This Matters

AX frontend complaints often look like general slowness, but the root action can be a single broad stock inquiry such as querying inventory across all dimensions. That pattern consumes SQL reads/CPU and AOS worker time, so other users experience slow forms.

## Dashboard Output

The Platform tab contains `AX Frontend Machine Impact Advisor` with:

- machine-impact query count
- critical count
- user and host/AOS ranking
- impacted inventory tables
- session id and query hash where available
- operator questions for localization
- containment and permanent fix hints

## Recommended Workflow

1. Identify the user/session/host.
2. Confirm whether the all-dimension stock inquiry is intentional.
3. If accidental, stop or narrow only through approved operations procedure.
4. Reproduce in TEST with restrictive filters.
5. Validate form/query ranges, display methods, caching, statistics and AX-compatible index coverage.
6. Re-run AXPA and compare logical reads, elapsed time and user impact.
