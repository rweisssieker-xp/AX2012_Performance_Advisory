# Security Policy

## Supported Use

This project is intended for read-only performance analysis of Dynamics AX 2012 and SQL Server environments.

## Reporting Issues

Do not include customer data, credentials, SQL text with sensitive values, or live evidence bundles in public issues.

## Secret Handling

The project expects secrets to be supplied through environment variables or local secret stores. Do not commit:

- SQL connection strings with passwords.
- Azure DevOps PATs.
- Jira API tokens.
- Power BI streaming endpoints.
- Live evidence exports.

## Data Handling

Use `scripts/mask_evidence.py` before sharing evidence outside the trusted operations team.

