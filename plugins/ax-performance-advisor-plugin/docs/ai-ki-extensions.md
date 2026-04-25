# More AI/KI Extensions

This pack adds AI-ready artifacts while staying evidence-grounded and auditable.

## Features

- Hypothesis ranking by playbook, severity points, evidence points, and confidence.
- Counterfactuals: do nothing, validate in TEST, implement after approval, rollback path.
- Causal narrative based on grouped root causes.
- LLM context pack with source policy and top findings.
- Embedding-friendly evidence chunks.
- Confidence calibration from declared confidence and evidence count.

## Run

```powershell
python .\scripts\ai_ki_extensions.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\ai-ki-extensions.json
```

The dashboard embeds these results in the `More AI/KI` tab.
