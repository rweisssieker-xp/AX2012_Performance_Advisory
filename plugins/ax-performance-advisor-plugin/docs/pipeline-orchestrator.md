# Pipeline Orchestrator

`scripts/run_axpa_pipeline.py` runs a complete AXPA read-only advisory workflow.

## Modes

- Analyze-only: uses an existing evidence folder.
- Collect + analyze: runs SQL and AX collectors first, then all outputs.

## Outputs

- findings JSON,
- technical Markdown report,
- HTML dashboard,
- autonomous ops pack,
- AI/KI extension pack,
- SQLite trend store,
- pipeline manifest with step status, durations, stdout/stderr excerpts and artifacts.

## Analyze Existing Evidence

```powershell
python .\scripts\run_axpa_pipeline.py `
  --environment bras3333-current `
  --server bras3333 `
  --database MicrosoftDynamicsGBLAX `
  --evidence .\evidence\bras3333-current `
  --out .\out
```

## Full Read-only Run

```powershell
python .\scripts\run_axpa_pipeline.py `
  --environment bras3333-current `
  --server bras3333 `
  --database MicrosoftDynamicsGBLAX `
  --evidence .\evidence\bras3333-current `
  --out .\out `
  --collect
```

The pipeline does not execute remediation. It collects and analyzes evidence only.
