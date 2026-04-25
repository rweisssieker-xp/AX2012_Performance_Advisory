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

## Evidence Classification

Treat these files as sensitive by default:

- SQL text, query plans, deadlock XML, Query Store exports.
- AX batch history, user sessions, AOS event logs, Trace Parser exports.
- DynamicsPerf exports and AX SQL trace exports.
- Dashboards and reports generated from live environments.

## Safe Disclosure

For public issues or pull requests:

- Use anonymized sample evidence.
- Replace server, database, company, user, customer, item, and path values.
- Attach only masked evidence packs.
- Describe missing permissions or collector failures without exposing credentials or internal hostnames.
