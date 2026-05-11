# Installation

This document describes how to install AX Performance Advisor from the internal release ZIP.

## Prerequisites

- Windows Server or Windows client for local analysis.
- Python 3.10 or newer available as `python`.
- PowerShell 5.1 or newer.
- Optional for development checks: `pytest`.
- Read-only SQL permissions when collecting live evidence:
  - `CONNECT` to the AX database.
  - `VIEW SERVER STATE` for server-level DMVs where permitted.
  - read access to relevant AX tables, SQL DMVs, Query Store and exported evidence sources.

The plugin is advisory-first. It writes local evidence, dashboard and report files only. It must not be granted rights such as `CREATE INDEX`, `ALTER`, `UPDATE`, `DELETE` or `DROP` for collection.

## 1. Download The Release

From GitHub Releases, download the release assets:

```text
https://github.com/rweisssieker-xp/AX2012_Performance_Advisory/releases/tag/v0.1.0
```

- `ax-performance-advisor-plugin-0.1.0.zip`
- `ax-performance-advisor-plugin-0.1.0.zip.manifest.json`
- optional: `ax-performance-advisor-plugin-0.1.0.sbom.json`
- optional: `ax-performance-advisor-plugin-0.1.0.integrity.json`

Recommended target directory:

```text
C:\Tools\AXPA
```

Recommended data directories outside the plugin folder:

```text
C:\AXPA\evidence
C:\AXPA\out
```

Keeping evidence/output outside the plugin folder prevents accidental data loss during updates.

Optional checksum verification:

```powershell
$manifest = Get-Content .\ax-performance-advisor-plugin-0.1.0.zip.manifest.json -Raw | ConvertFrom-Json
$actual = (Get-FileHash .\ax-performance-advisor-plugin-0.1.0.zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $manifest.sha256) { throw "ZIP checksum mismatch" }
```

## 2. Unpack

```powershell
New-Item -ItemType Directory -Force C:\Tools\AXPA | Out-Null
Expand-Archive `
  -Path .\ax-performance-advisor-plugin-0.1.0.zip `
  -DestinationPath C:\Tools\AXPA `
  -Force

cd C:\Tools\AXPA\ax-performance-advisor-plugin
```

Expected structure:

```text
C:\Tools\AXPA\ax-performance-advisor-plugin
├─ .codex-plugin\plugin.json
├─ .mcp.json
├─ .app.json
├─ skills\
├─ scripts\
├─ docs\
├─ rules\
├─ sample\
└─ tests\
```

## 3. Verify The Installation

```powershell
python --version
python -m json.tool .\.codex-plugin\plugin.json > $null
python -m json.tool .\.mcp.json > $null
python -m compileall .\scripts .\tests
```

If `pytest` is missing:

```powershell
python -m pip install -r .\requirements.txt
```

Run the test suite:

```powershell
python -m pytest .\tests -q
```

## 4. Generate A Sample Dashboard

```powershell
python .\scripts\generate_dashboard.py `
  --evidence .\sample\evidence `
  --output .\out\sample-dashboard.html
```

Open:

```text
C:\Tools\AXPA\ax-performance-advisor-plugin\out\sample-dashboard.html
```

## 5. Install As Codex Plugin

The unpacked folder already contains the Codex plugin manifest:

```text
.codex-plugin\plugin.json
```

Use one of these internal approaches:

1. Keep the plugin under `C:\Tools\AXPA\ax-performance-advisor-plugin` and point Codex/plugin discovery to that folder if your Codex setup supports local plugin paths.
2. Copy the unpacked folder into your organization's standard Codex plugin directory.
3. Keep the Git repository as source of truth and let users pull the plugin folder from GitHub/Azure DevOps.

After Codex has loaded the plugin, the available skill surface is under:

```text
skills\
```

The MCP server definition is:

```text
.mcp.json
```

It defaults to:

```text
AXPA_READ_ONLY=true
```

## 6. Collect Live Evidence Read-Only

Create an evidence folder per environment and run collectors with read-only credentials.

Example:

```powershell
$evidence = "C:\AXPA\evidence\bras3333-$(Get-Date -Format yyyyMMdd-HHmmss)"
New-Item -ItemType Directory -Force $evidence | Out-Null

.\scripts\collect_sql_snapshot.ps1 `
  -ConnectionString "Server=BRAS3333;Database=MicrosoftDynamicsGBLAX;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory $evidence `
  -AxDatabaseName MicrosoftDynamicsGBLAX `
  -IncludeQueryStore `
  -IncludeDeadlocks

.\scripts\collect_ax_db_snapshot.ps1 `
  -ConnectionString "Server=BRAS3333;Database=MicrosoftDynamicsGBLAX;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" `
  -OutputDirectory $evidence `
  -Days 14
```

Only use this with an approved read-only account. Do not run collectors with schema-owner or sysadmin rights unless explicitly approved for a controlled test.

## 7. Generate The Environment Dashboard

```powershell
$run = Split-Path $evidence -Leaf
$out = "C:\AXPA\out\$run"
New-Item -ItemType Directory -Force $out | Out-Null

python .\scripts\generate_dashboard.py `
  --evidence $evidence `
  --output "$out\$run-dashboard.html"
```

Optional HTTP smoke test:

```powershell
python .\scripts\qa_dashboard_http.py `
  --root . `
  --dashboard "$out\$run-dashboard.html" `
  --require "CEO Cockpit" `
  --require "Operator Cockpit" `
  --require "Batch Control Tower" `
  --output "$out\dashboard-http-qa.json"
```

## 8. Update

```powershell
cd C:\Tools\AXPA
Rename-Item .\ax-performance-advisor-plugin .\ax-performance-advisor-plugin-old
Expand-Archive `
  -Path .\ax-performance-advisor-plugin-0.1.0.zip `
  -DestinationPath C:\Tools\AXPA `
  -Force
```

If you followed the recommended `C:\AXPA\evidence` and `C:\AXPA\out` layout, updates do not touch collected evidence or generated dashboards. If you stored evidence/output inside the old plugin folder, copy them out before deleting `ax-performance-advisor-plugin-old`.

## 9. Uninstall

Remove the unpacked folder:

```powershell
Remove-Item C:\Tools\AXPA\ax-performance-advisor-plugin -Recurse
```

Remove local evidence/output folders only if they are no longer needed and retention rules allow deletion.

## 10. Troubleshooting

`python` not found:

```powershell
py -3 --version
```

`pytest` missing:

```powershell
python -m pip install -r .\requirements.txt
```

Dashboard opens but buttons do not react:

```powershell
python .\scripts\generate_dashboard.py `
  --evidence .\sample\evidence `
  --output .\out\sample-dashboard.html
python .\scripts\qa_dashboard_http.py `
  --root . `
  --dashboard .\out\sample-dashboard.html `
  --require "CEO Cockpit" `
  --require "Root Cause Chat" `
  --output .\out\sample-dashboard-qa.json
```

Collector returns permission errors:

- Verify that the SQL account has read-only DMV/table permissions.
- Keep the `.error.csv` files in the evidence folder; the dashboard will show collector gaps.
- Do not grant write permissions just to silence collector errors.
