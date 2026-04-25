# Strategy Extensions

This pack adds planning and decision-support views.

## Features

- What-if simulation for resolving dominant playbook groups.
- Baseline benchmark for the current run.
- Evidence completeness roadmap.
- Remediation Kanban lanes: Now, Next, Later, Waiting Evidence.
- KPI contracts per playbook.
- Capability matrix showing implemented, guarded, configured, and evidence-gated features.

## Run

```powershell
python .\scripts\strategy_extensions.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\strategy-extensions.json
```

The dashboard embeds these results in the `Strategy` tab.
