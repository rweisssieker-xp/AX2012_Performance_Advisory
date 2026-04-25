---
name: azure-devops-jira-export
description: Export or push AXPA findings as Azure DevOps or Jira tickets with dry-run support and credential checks.
---

# Azure DevOps And Jira Export

Use this skill when findings must become operational tickets.

## Workflow

1. Generate CSV with `export_ticket_backlog.py`.
2. Push to Azure DevOps with `push_azure_devops_tickets.py` when env vars are configured.
3. Push to Jira with `push_jira_tickets.py` when env vars are configured.
4. Use `--dry-run` before live push.

