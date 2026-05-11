# Release And Test Runbook

This runbook describes how to package and test AX Performance Advisor before sharing it internally or publishing a GitHub release.

## 1. Local Verification

Run from the repository root:

```powershell
python -m compileall .\plugins\ax-performance-advisor-plugin\scripts .\plugins\ax-performance-advisor-plugin\tests
python -m pytest .\plugins\ax-performance-advisor-plugin\tests -q
```

## 2. Generate Sample Outputs

Use sample evidence for release validation. Do not require customer/live evidence for a general release check.

```powershell
python .\plugins\ax-performance-advisor-plugin\scripts\generate_dashboard.py `
  --evidence .\plugins\ax-performance-advisor-plugin\sample\evidence `
  --output .\plugins\ax-performance-advisor-plugin\out\sample-dashboard.html

python .\plugins\ax-performance-advisor-plugin\scripts\ai_insights.py `
  --evidence .\plugins\ax-performance-advisor-plugin\sample\evidence `
  --output .\plugins\ax-performance-advisor-plugin\out\sample-ai-insights.json `
  --markdown-output .\plugins\ax-performance-advisor-plugin\out\sample-ai-insights.md `
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
- `install_from_github.ps1`
- `skills/`
- `scripts/`
- `rules/`
- `docs/`
- `INSTALL.md`
- `README.md`
- `LICENSE`
- `RELEASE_NOTES.md`

Exclude:

- `evidence/`
- `out/`
- `__pycache__/`
- credentials, connection strings, server secrets, raw customer data

## 6. Build Distribution Artifacts

Run from `plugins/ax-performance-advisor-plugin`:

```powershell
python .\scripts\build_sbom.py `
  --root . `
  --output .\dist\ax-performance-advisor-plugin-0.1.0.sbom.json

python .\scripts\plugin_integrity.py `
  --root . `
  --output .\dist\ax-performance-advisor-plugin-0.1.0.integrity.json

python .\scripts\build_release_package.py `
  --root . `
  --version 0.1.0 `
  --output .\dist\ax-performance-advisor-plugin-0.1.0.zip
```

Attach `install_from_github.ps1`, the ZIP, `.manifest.json`, SBOM, integrity manifest, and `RELEASE_NOTES.md` to the internal release.

## 7. Post-Release Check

Download or expand the uploaded ZIP into a temporary folder and verify:

```powershell
Expand-Archive .\ax-performance-advisor-plugin-0.1.0.zip -DestinationPath $env:TEMP\axpa-release-check -Force
cd $env:TEMP\axpa-release-check\ax-performance-advisor-plugin
Test-Path .\INSTALL.md
python -m json.tool .\.codex-plugin\plugin.json > $null
python .\scripts\generate_dashboard.py --evidence .\sample\evidence --output .\out\sample-dashboard.html
```
