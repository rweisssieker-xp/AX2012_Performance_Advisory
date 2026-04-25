# Contributing

## Workflow

1. Create a focused branch for the change.
2. Keep collectors read-only unless the change is explicitly an admin-approved execution feature.
3. Add or update tests for new analyzers, advisory packs, scripts, or output schemas.
4. Update documentation for any user-facing script, skill, report, dashboard tab, or integration.
5. Run the development checks before opening a PR.

## Development Checks

Run from repository root:

```powershell
python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests
python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v
python -m json.tool plugins/ax-performance-advisor-plugin/.codex-plugin/plugin.json
```

## Documentation Checks

- Add new user-facing scripts to `plugins/ax-performance-advisor-plugin/scripts/README.md`.
- Add feature docs under `plugins/ax-performance-advisor-plugin/docs/`.
- Link important docs from `plugins/ax-performance-advisor-plugin/docs/INDEX.md`.
- Keep examples read-only and avoid real customer names, IDs, SQL text, and credentials.

## Rules

- Keep collectors read-only.
- Do not commit live `evidence/`, generated `out/`, secrets, credentials, or customer data.
- Add tests or sample evidence for new analyzers.
- Document new scripts in `plugins/ax-performance-advisor-plugin/scripts/README.md`.
- Do not mark a feature as real unless it is generated from evidence or explicitly reports missing evidence.
- Do not add automatic production remediation without approval gates, rollback notes, validation evidence, and documentation.
