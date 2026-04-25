# Contributing

## Development Checks

Run from repository root:

```powershell
python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests
python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v
python -m json.tool plugins/ax-performance-advisor-plugin/.codex-plugin/plugin.json
```

## Rules

- Keep collectors read-only.
- Do not commit live `evidence/`, generated `out/`, secrets, credentials, or customer data.
- Add tests or sample evidence for new analyzers.
- Document new scripts in `plugins/ax-performance-advisor-plugin/scripts/README.md`.

