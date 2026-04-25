# Testing Guide

Run checks from the repository root unless noted otherwise.

## Core Checks

```powershell
python -m compileall plugins/ax-performance-advisor-plugin/scripts plugins/ax-performance-advisor-plugin/tests
python -m unittest discover -s plugins/ax-performance-advisor-plugin/tests -v
```

## Manifest Checks

```powershell
python -m json.tool plugins/ax-performance-advisor-plugin/.codex-plugin/plugin.json
python -m json.tool plugins/ax-performance-advisor-plugin/.mcp.json
python -m json.tool plugins/ax-performance-advisor-plugin/.app.json
python -m json.tool plugins/ax-performance-advisor-plugin/config.example.json
python -m json.tool plugins/ax-performance-advisor-plugin/masking-policy.example.json
```

## Dashboard Smoke Test

```powershell
python plugins\ax-performance-advisor-plugin\scripts\generate_dashboard.py `
  --evidence plugins\ax-performance-advisor-plugin\sample\evidence `
  --output plugins\ax-performance-advisor-plugin\out\dashboard.html
```

Then open `plugins/ax-performance-advisor-plugin/out/dashboard.html` and check:

- main KPI cards render
- findings table is populated
- AI/KI tabs render
- Autonomous AI and Autonomous Ops tabs render
- no browser JavaScript errors occur

## Skill Checks

Each skill must have a `SKILL.md` file with YAML frontmatter:

```text
---
name: skill-name
description: What the skill does.
---
```

## Release Checks

Before publishing or tagging:

- unit tests pass
- plugin manifests are valid JSON
- no `evidence/`, `out/`, credentials, or live customer exports are staged
- README and docs index mention new user-facing features
- new scripts are documented in `scripts/README.md`
