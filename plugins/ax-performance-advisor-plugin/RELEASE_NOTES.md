# Release Notes

## 0.1.0

Initial internal distribution package for AX Performance Advisor.

### Highlights

- Read-only AX 2012 R3 and SQL Server 2016 evidence analysis.
- Installation guide for ZIP distribution, Codex setup, smoke tests, update and uninstall.
- Interactive dashboard with CEO Cockpit, Operator Cockpit, Batch Control Tower, Platform Extensions and AI/KI advisory sections.
- AX-specific batch collision analysis, live blocking interpretation, frontend/user/client impact radar and X++ attribution readiness.
- Governance artifacts for CAB/GxP, recommendation lifecycle, evidence gaps, ticket drafts and board-ready reports.
- Local-only packaging scripts with SBOM, integrity manifest and checksummed ZIP.
- GitHub installer `install_from_github.ps1` installs the release ZIP from GitHub and verifies the manifest checksum.
- Installer safety update: `config.toml` is not modified by default; the installer writes `codex-config-snippet.toml`. Automatic config updates require `-UpdateCodexConfig`, create a backup, use a managed marker block, and validate TOML before replacing the file.

### Safety

- No release package includes local `evidence/` or `out/` folders.
- Default MCP environment sets `AXPA_READ_ONLY=true`.
- Dashboard and reports write local files only.
- Database changes are not executed by the dashboard.

### Verification

Before publishing this release, run:

```powershell
python -m compileall .\scripts .\tests
python -m pytest .\tests -q
python .\scripts\build_release_package.py --root . --version 0.1.0 --output .\dist\ax-performance-advisor-plugin-0.1.0.zip
```
