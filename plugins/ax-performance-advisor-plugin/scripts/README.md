# Scripts

This folder contains the first working AX Performance Advisor MVP tools.

Implemented scripts:

- `mcp_server.py`: read-only MCP server exposing collector and analysis tools.
- `collect_sql_snapshot.ps1`: SQL Server 2016 DMV snapshot collector.
- `collect_ax_events.ps1`: AOS event log and performance counter collector.
- `collect_ax_db_snapshot.ps1`: AX database collector for batch, sessions, AIF, and retail load evidence.
- `collect_aos_counters.ps1`: AOS/performance counter collector.
- `import_trace_parser_export.py`: Trace Parser export normalizer.
- `import_dynamicsperf_export.py`: DynamicsPerf export normalizer.
- `parse_deadlock_xml.py`: SQL Server deadlock XML parser.
- `parse_plan_xml.py`: SQL Server execution plan XML parser.
- `analyze_evidence.py`: generates normalized findings from an evidence directory.
- `generate_report.py`: Markdown/HTML report generator.
- `generate_html_report.py`: standalone HTML report generator.
- `mask_evidence.py`: creates a masked evidence copy for sharing and audit review.
- `update_trend_store.py`: persists findings into a SQLite trend store.
- `generate_validation_scripts.py`: creates read-only validation SQL per finding.
- `collect_ax_model_mapping.ps1`: reads AX model database metadata for class/object mapping.
- `collect_ax_sql_trace.ps1`: reads `SysTraceTableSQL` when AX SQL tracing is enabled.
- `collect_dynamicsperf_snapshot.ps1`: inventories a DynamicsPerf database.
- `push_azure_devops_tickets.py`: creates Azure DevOps work items when credentials are provided.
- `push_jira_tickets.py`: creates Jira issues when credentials are provided.
- `push_powerbi_dataset.py`: pushes JSON rows to a Power BI streaming endpoint.
- `generate_dashboard.py`: creates an interactive local HTML dashboard.
- `autonomous_ops.py`: creates the Autonomous Ops pack with investigation queues, follow-up questions, evidence acquisition plans, change drafts, validation plans, readiness gates, next-best actions, and executive risk briefings.
- `evidence_health.py`: summarizes source completeness, empty files, collector errors, AX schema discovery, and source status.
- `skill_catalog.py`: groups plugin skills into primary and advanced capability categories.
- `compare_environments.py`: compares multiple evidence directories for cross-machine or test-vs-prod dashboard context.
- `check_sql_permissions.ps1`: verifies read-only SQL permission posture.
- `setup_scheduled_task.ps1`: registers a Windows scheduled task for AXPA automation.
- `plugin_integrity.py`: creates or verifies plugin code integrity manifests.
- `run_script` MCP tool: exposes allowlisted Python scripts through the MCP server.
- `generate_cab_package.py`: CAB/change-control package generator.
- `compare_baseline.py`: before/after comparator for deployments, tuning actions, and batch schedule changes.
- `export_evidence_pack.py`: bundles raw evidence, findings, approvals, and validation results for audit or change management.
- `export_powerbi_dataset.py`: creates dashboard-ready datasets for executive reporting.
- `export_ticket_backlog.py`: Jira/Azure DevOps compatible CSV backlog export.
- `flight_recorder.py`: scheduled lightweight evidence snapshot recorder.
- `incident_replay.py`: reconstructs an incident timeline from evidence.
- `score_root_cause_confidence.py`: ranks root-cause confidence.
- `customization_risk_map.py`: maps custom-code performance risk.
- `simulate_batch_schedule.py`: creates a batch conflict matrix.
- `fingerprint_workload.py`: classifies workload windows.
- `generate_table_heatmap.py`: scores hot AX tables.
- `simulate_change_risk.py`: profiles planned remediation risk.
- `calibrate_thresholds.py`: derives local thresholds from evidence.
- `match_known_issues.py`: maps findings to known issue patterns.
- `optimize_maintenance_window.py`: proposes maintenance/batch sequencing.
- `data_lifecycle_roi.py`: estimates archive/cleanup impact.
- `correlate_model_deployments.py`: correlates changes with findings.
- `build_repro_checklist.py`: creates test-vs-prod reproduction checklist.
- `generate_executive_narrative.py`: writes board-ready risk narrative.
- `check_performance_budgets.py`: validates process/query budgets.
- `continuous_improvement_scorecard.py`: creates governance scorecard.
- `manage_index_governance.py`: exports index candidate lifecycle backlog.
- `analyze_query_families.py`: groups related query pressure.
- `auto_triage.py`: routes findings by operational lane.
- `check_slos.py`: evaluates AX process and query SLOs.
- `detect_anomalies.py`: compares current evidence with trend baseline.
- `release_gate.py`: passes/fails deployment evidence comparison.
- `watch_plan_regressions.py`: exports SQL plan-regression candidates.
- `custom_code_ownership_graph.py`: exports custom-code/finding ownership graph.
- `estimate_cost_of_delay.py`: estimates daily risk cost of findings.
- `grade_evidence_quality.py`: assigns A-D evidence grades.
- `simulate_recommendation_scenarios.py`: expands findings into scenario options.
- `compliance_mode_check.py`: checks GxP/CAB required fields.
- `create_chain_of_custody.py`: hashes evidence files into custody manifest.
- `map_workload_calendar.py`: maps findings to business calendar windows.
- `forecast_capacity_exhaustion.py`: forecasts data/latency pressure.
- `retention_policy_advisor.py`: proposes table retention review policies.
- `capture_knowledge_feedback.py`: appends finding outcomes to a feedback KB.
- `fleet_view.py`: summarizes multiple environments.
- `generate_runbook.py`: creates operations runbook.
- `correlate_sql_agent_jobs.py`: correlates SQL Agent and AX batch evidence.
- `aos_topology_advisor.py`: reviews AOS/batch topology.
- `archiving_impact_sandbox.py`: simulates archive impact.
- `root_cause_narrative.py`: creates cause-and-effect narrative.
- `update_performance_debt_register.py`: persists recurring findings, owners, deferment reasons, and next decisions.
- `predict_sla_breach.py`: forecasts batch and close-window SLA breach risk from runtime and data-growth trends.
- `detect_deployment_regression.py`: compares before/after evidence around deployments or configuration changes.
- `compare_environment_drift.py`: compares SQL, AX, data-volume, maintenance, and batch setup across environments.
- `map_table_ownership.py`: maps AX tables and custom objects to business and technical owners.
- `generate_action_playbook.py`: expands a finding into a diagnostic and remediation playbook.

Collectors should default to read-only behavior and write timestamped evidence bundles for auditability.

## Quick Start

Run the sample analysis:

```powershell
python .\scripts\analyze_evidence.py --evidence .\sample\evidence --output .\out\findings.json
python .\scripts\generate_report.py --evidence .\sample\evidence --output .\out\report.md
python .\scripts\export_evidence_pack.py --evidence .\sample\evidence --output .\out\evidence-pack.zip
python .\scripts\export_powerbi_dataset.py --evidence .\sample\evidence --output .\out\powerbi-findings.csv
python .\scripts\generate_html_report.py --evidence .\sample\evidence --output .\out\report.html
python .\scripts\generate_validation_scripts.py --evidence .\sample\evidence --output-dir .\out\validation
python .\scripts\update_trend_store.py --evidence .\sample\evidence --db .\out\axpa-trends.sqlite
```

Collect SQL evidence from a SQL Server using a read-only connection:

```powershell
.\scripts\collect_sql_snapshot.ps1 -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" -OutputDirectory .\evidence\prod-snapshot
```

Include deeper SQL evidence:

```powershell
.\scripts\collect_sql_snapshot.ps1 -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" -OutputDirectory .\evidence\prod-snapshot -AxDatabaseName AXDB -IncludeQueryStore -IncludeDeadlocks
```

Collect AX-related Windows event log evidence:

```powershell
.\scripts\collect_ax_events.ps1 -OutputDirectory .\evidence\prod-snapshot -Hours 24
```

Collect AX database and AOS counter evidence:

```powershell
.\scripts\collect_ax_db_snapshot.ps1 -ConnectionString "Server=SERVER;Database=AXDB;Integrated Security=True;Application Name=AXPA;TrustServerCertificate=True" -OutputDirectory .\evidence\prod-snapshot -Days 14
.\scripts\collect_aos_counters.ps1 -OutputDirectory .\evidence\prod-snapshot -SampleSeconds 30
```

## Evidence Bundle Layout

Recommended output layout:

- `metadata.json`: environment, time window, collector version, analysis version, and source hashes.
- `sql/`: DMV snapshots, wait deltas, plans, blocking chains, deadlocks, file latency, TempDB, Query Store exports.
- `ax/`: batch history, AOS counters, event logs, user sessions, Trace Parser exports, DynamicsPerf extracts.
- `calendar/`: business windows, maintenance windows, deployments, and known operational events.
- `findings/`: normalized findings with severity, confidence, change-readiness score, status, and validation state.
- `debt/`: performance debt register snapshots and ownership state.
- `forecast/`: SLA breach predictions and capacity-planning signals.
- `drift/`: production/test/pre-production drift comparisons.
- `ownership/`: table, module, customization, support queue, and owner mappings.
- `playbooks/`: generated diagnostic and remediation playbooks.
- `reports/`: technical report, management summary, and dashboard extracts.
