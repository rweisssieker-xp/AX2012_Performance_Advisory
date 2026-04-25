# Release And Test Runbook

This runbook describes how to package and test AX Performance Advisor before sharing it internally or publishing a GitHub release.

## 1. Local Verification

Run from the repository root:

```powershell
python -m compileall .\plugins\ax-performance-advisor-plugin\scripts .\plugins\ax-performance-advisor-plugin\tests
python -m unittest discover -s .\plugins\ax-performance-advisor-plugin\tests -v
```

## 2. Generate IT-TEST-ERP4CU Outputs

```powershell
python .\plugins\ax-performance-advisor-plugin\scripts\generate_dashboard.py `
  --evidence .\plugins\ax-performance-advisor-plugin\evidence\IT-TEST-ERP4CU `
  --output .\plugins\ax-performance-advisor-plugin\out\IT-TEST-ERP4CU-dashboard.html

python .\plugins\ax-performance-advisor-plugin\scripts\ai_insights.py `
  --evidence .\plugins\ax-performance-advisor-plugin\evidence\IT-TEST-ERP4CU `
  --output .\plugins\ax-performance-advisor-plugin\out\IT-TEST-ERP4CU-ai-insights.json `
  --markdown-output .\plugins\ax-performance-advisor-plugin\out\IT-TEST-ERP4CU-ai-insights.md `
  --question "Warum war AX langsam?"
```

## 3. MCP Smoke Test

Use the `generate_ai_insights` MCP tool or call the server through a JSON-RPC client. The expected result includes `features: 20` and a non-zero finding count.

## 4. Release Checklist

- Plugin manifest JSON validates.
- MCP manifest JSON validates.
- App manifest JSON validates.
- Skill frontmatter validates.
- Tests pass.
- Generated dashboard opens locally.
- Evidence packs do not contain secrets or unmasked sensitive data.
- Collector `.error.csv` files are reviewed and either fixed or documented as environment limitations.

## 5. Release Contents

Include:

- `.codex-plugin/plugin.json`
- `.mcp.json`
- `.app.json`
- `skills/`
- `scripts/`
- `rules/`
- `docs/`
- `README.md`
- `LICENSE`

Exclude:

- `evidence/`
- `out/`
- `__pycache__/`
- credentials, connection strings, server secrets, raw customer data
