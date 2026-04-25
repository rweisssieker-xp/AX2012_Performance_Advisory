# AXPA Threat Model

## Assets

- SQL/AX evidence files.
- Generated findings, reports, dashboards, tickets, and evidence packs.
- Admin execution previews and confirmation tokens.
- Optional external integration credentials.

## Main Risks

- Accidental production change from advisory output.
- Sensitive data leakage through evidence packs or notifications.
- Credential leakage in config files or logs.
- Overbroad SQL permissions for collectors.
- Misleading recommendations from incomplete evidence.

## Controls

- Read-only default mode.
- Admin execution preview only, with gates and tokens.
- Secret readiness checks that do not print values.
- Evidence masking support.
- Collector errors and evidence gaps surfaced explicitly.
- Release package excludes `out`, `evidence`, and caches.

## Required Production Additions

- Store credentials in approved secret manager.
- Sign release packages.
- Restrict dashboard and evidence access by role.
- Review generated scripts before execution.
- Attach evidence pack and rollback to every change.
