---
name: index-risk-review
description: Review SQL Server missing-index and plan-warning evidence through AX-specific risk, write overhead, existing index overlap, and rollback guidance.
---

# Index Risk Review

Use this skill for missing-index candidates, plan missing-index warnings, and high-read AX table findings.

## Workflow

1. Run `scripts/manage_index_governance.py`.
2. Check table family risk using `rules/index_risk_rules.yml`.
3. Validate AX key patterns: `Partition`, `DataAreaId`, `RecId`, status/date fields.
4. Produce candidate-review output, not direct `CREATE INDEX` instructions.

## Related Scripts

- `manage_index_governance.py`
- `generate_validation_scripts.py`
- `simulate_change_risk.py`

