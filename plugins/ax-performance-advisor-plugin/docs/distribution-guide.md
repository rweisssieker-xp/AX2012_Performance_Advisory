# Distribution Guide

This guide describes how to distribute AX Performance Advisor internally.

## Release Package

Build from the plugin root:

```powershell
python -m compileall .\scripts .\tests
python -m pytest .\tests -q
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

The ZIP intentionally excludes:

- `evidence/`
- `out/`
- `dist/`
- `__pycache__/`
- `.pytest_cache/`
- local logs and Python bytecode

## Recipient Install

See the full installation guide in [`../INSTALL.md`](../INSTALL.md).

Direct Codex install from GitHub release:

```powershell
Invoke-WebRequest `
  -Uri "https://github.com/rweisssieker-xp/AX2012_Performance_Advisory/releases/download/v0.1.0/install_from_github.ps1" `
  -OutFile ".\install_from_github.ps1"
powershell -ExecutionPolicy Bypass -File .\install_from_github.ps1 -Force
```

Minimum recipient install:

```powershell
New-Item -ItemType Directory -Force C:\Tools\AXPA | Out-Null
Expand-Archive .\ax-performance-advisor-plugin-0.1.0.zip -DestinationPath C:\Tools\AXPA -Force
cd C:\Tools\AXPA\ax-performance-advisor-plugin
python -m pip install -r .\requirements.txt
python -m pytest .\tests -q
```

Run a local sample dashboard:

```powershell
python .\scripts\generate_dashboard.py `
  --evidence .\sample\evidence `
  --output .\out\sample-dashboard.html
```

## Codex Plugin Install

Install or copy the unpacked folder so Codex can see:

```text
ax-performance-advisor-plugin/
├─ .codex-plugin/plugin.json
├─ .mcp.json
├─ .app.json
├─ skills/
├─ scripts/
├─ rules/
├─ docs/
└─ sample/
```

The plugin manifest points to `skills/`, `.mcp.json`, and `.app.json`.

## GitHub / Azure DevOps Distribution

Use the repository as the source of truth and attach the ZIP plus manifest files to a release.

Current GitHub release:

```text
https://github.com/rweisssieker-xp/AX2012_Performance_Advisory/releases/tag/v0.1.0
```

Recommended release artifacts:

- `install_from_github.ps1`
- `ax-performance-advisor-plugin-0.1.0.zip`
- `ax-performance-advisor-plugin-0.1.0.zip.manifest.json`
- `ax-performance-advisor-plugin-0.1.0.sbom.json`
- `ax-performance-advisor-plugin-0.1.0.integrity.json`
- release notes

## Safety Boundary

The distributed plugin is advisory-first and read-only by default.

- Collectors should use least-privilege read-only credentials.
- The dashboard does not execute database changes.
- Admin execution artifacts are generated as proposals only.
- Any TEST or PROD remediation must be executed outside the dashboard by an approved admin process.
- Release packages must not contain live `evidence/` or generated `out/` data.
