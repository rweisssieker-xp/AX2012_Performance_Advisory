"""Placeholder MCP server for the AX Performance Advisor plugin.

The production server should expose read-only tools for:
- SQL Server evidence collection.
- AOS event and performance-counter collection.
- DynamicsPerf and Trace Parser import.
- Business-calendar and change-history import.
- Finding generation and prioritization.
- Before/after comparison.
- Audit evidence-pack export.
- Markdown, HTML, Power BI, Jira, or Azure DevOps report outputs.
"""


def main() -> None:
    raise SystemExit(
        "AX Performance Advisor MCP server is a placeholder. "
        "Implement read-only collector tools before enabling this server."
    )


if __name__ == "__main__":
    main()
