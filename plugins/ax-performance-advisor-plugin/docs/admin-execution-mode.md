# Admin Execution Mode

Admin Execution Mode turns recommendations into guarded implementation previews. It does not execute production changes from the dashboard.

## Guardrails

- Default mode is `preview-only`.
- Allowed environments are configured in `rules/execution_policy.json`.
- PROD requires separate operational execution and second confirmation.
- Every action has a confirmation token.
- Every action needs approval reference, rollback note, validation metric, and audit entry.
- The dashboard displays generated scripts and gates, but it does not run SQL or AX changes.

## Generate

```powershell
python .\scripts\admin_execution.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output-dir .\out\admin-execution `
  --environment TEST `
  --minimum-severity high
```

To mark a single action as executable-after-final-review, rerun with the action's token and an approval reference:

```powershell
python .\scripts\admin_execution.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output-dir .\out\admin-execution `
  --environment TEST `
  --minimum-severity high `
  --approval-reference "CHG-12345" `
  --confirm-token "TOKEN_FROM_PLAN"
```

The generated SQL files are previews. A DBA/AX admin must review and execute them through approved tooling.
