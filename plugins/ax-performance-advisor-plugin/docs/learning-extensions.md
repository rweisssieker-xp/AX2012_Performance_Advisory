# AI Learning Extensions

This pack adds learning and decision-quality artifacts.

## Features

- Recommendation memory in SQLite.
- Similarity search across findings.
- Acceptance simulation for remediation strategies.
- Executive narrative variants for CIO, DBA, QA/GxP, and process owner.
- Anomaly explanations with confirm/disprove criteria.
- Action confidence tuning.

## Run

```powershell
python .\scripts\learning_extensions.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output-dir .\out\learning
```

The dashboard embeds these results in the `AI Learning` tab.
