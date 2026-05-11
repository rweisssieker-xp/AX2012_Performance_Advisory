# Documentation Flow Check

This checklist records the intended end-to-end documentation path for AX Performance Advisor.

## Primary Reader Flow

1. Open `README.md`.
2. Follow `INSTALL.md` for release ZIP installation.
3. Verify manifests and run the sample dashboard.
4. Use `docs/operations-guide.md` for read-only evidence collection.
5. Generate the environment dashboard.
6. Use `docs/distribution-guide.md` and `docs/release-runbook.md` for internal release packaging.

## Completeness Checklist

- [x] Release download location is documented.
- [x] ZIP checksum verification is documented.
- [x] Python, PowerShell and pytest prerequisites are documented.
- [x] Plugin folder layout is documented.
- [x] Codex plugin manifest location is documented.
- [x] Direct GitHub-to-Codex installer is documented.
- [x] MCP manifest location and read-only default are documented.
- [x] Sample dashboard smoke test is documented.
- [x] Live evidence collection is documented as read-only.
- [x] Evidence/output directories outside the plugin folder are recommended.
- [x] Dashboard HTTP QA is documented.
- [x] Update and uninstall procedures are documented.
- [x] Release packaging, SBOM and integrity manifests are documented.
- [x] Post-release ZIP install check is documented.

## Intentional Boundaries

- The docs do not prescribe granting write permissions to SQL or AX.
- Productive push integrations require separate credentials and approval.
- Admin remediation remains outside the dashboard and must follow local CAB/GxP controls.
- Customer-specific server names are examples only; general release validation uses `sample/evidence`.

## Known Follow-Ups

- Add organization-specific Codex local plugin installation path when the internal Codex deployment standard is final.
- Add exact SQL read-only role script if the DBA team approves a standard permission model.
- Add service account naming and credential rotation policy when operations ownership is finalized.
