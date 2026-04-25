# Governance Extensions

This pack adds operational governance artifacts around the technical findings.

## Features

- Runbook automation steps per top finding.
- RACI matrix by owner.
- Business impact timeline.
- Suppression governance candidates with expiry and approval requirements.
- Evidence/data-quality score, empty file detection, collector error list, duplicate finding IDs.
- Audit CSV/JSON export for QA, CAB, and GxP review.

## Run

```powershell
python .\scripts\governance_extensions.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output-dir .\out\governance
```

The dashboard embeds these results in the `Governance` tab.
