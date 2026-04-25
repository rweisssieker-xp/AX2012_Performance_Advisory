# Optional Agent, RBAC, RAG, X++ Attribution, Release Packaging

## Optional Agent

The optional agent is not required for the plugin. It is a local scheduled runner for environments that want continuous refresh.

Dry-run install:

```powershell
.\scripts\install_optional_agent.ps1 `
  -ConfigPath .\config\optional-agent.example.json `
  -DryRun
```

One-shot run:

```powershell
python .\scripts\optional_agent.py --config .\config\optional-agent.example.json --once
```

## RBAC Portal

Static role entry points can be generated from the dashboard:

```powershell
python .\scripts\rbac_portal.py `
  --dashboard .\out\IT-TEST-ERP4CU-dashboard.html `
  --output-dir .\out\rbac-portal
```

This creates role-labeled dashboard files for viewer, DBA, AX admin, QA/GxP, CIO, and admin.

## Local RAG/Q&A

The local RAG/Q&A utility indexes findings and returns source finding IDs. It does not require an external LLM.

```powershell
python .\scripts\rag_qa.py `
  --evidence .\evidence\IT-TEST-ERP4CU `
  --output .\out\rag-qa.json `
  --question "blocking batch query"
```

## X++ Attribution

`xpp_attribution.py` maps findings to normalized Trace Parser or DynamicsPerf rows when `trace_parser.csv` or `dynamicsperf_trace.csv` exists in the evidence directory. Without those files it reports `requires-trace-evidence` rather than inventing mappings.

## Release Package

```powershell
python .\scripts\build_release_package.py `
  --root . `
  --output .\out\release\ax-performance-advisor-plugin.zip
```

The package excludes `out`, `evidence`, and cache files, then writes a SHA-256 manifest.
