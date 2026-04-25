# Optional Agent Service Hardening

The optional agent is intentionally separate from the plugin runtime.

## Current State

- `optional_agent.py` supports one-shot and loop modes.
- `install_optional_agent.ps1` supports Scheduled Task dry-run and registration.

## Production Hardening Checklist

- Run under dedicated low-privilege service account.
- Use read-only SQL permissions.
- Store secrets outside config files.
- Enable Windows task history or service logs.
- Configure retry/backoff and alert on repeated failure.
- Pin plugin version and verify release manifest before update.
- Keep `evidence` and `out` directories ACL-restricted.
