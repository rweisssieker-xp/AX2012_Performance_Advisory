# Security Model

AX Performance Advisor is read-only by default.

## SQL Permissions

Recommended minimum:

- Connect to AX database.
- Read selected AX operational tables needed for batch/session/service evidence.
- `VIEW SERVER STATE` for server-wide DMVs where approved.
- `VIEW DATABASE STATE` for database-level DMVs and Query Store.
- No `CREATE`, `ALTER`, `UPDATE`, `DELETE`, `INSERT`, or `DROP` permissions.

## Secrets

Scripts accept credentials through connection strings or environment variables. Do not commit secrets. For API push scripts, use:

- `AZDO_ORG_URL`, `AZDO_PROJECT`, `AZDO_PAT`
- `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `POWERBI_PUSH_ENDPOINT`

## Data Protection

Use `mask_evidence.py` before sharing evidence outside the operations team. It masks common user, host, login, SQL text, and client fields.

## Audit

Evidence packs, CAB packages, trend store rows, and validation scripts provide an audit trail from finding to recommendation and validation.
