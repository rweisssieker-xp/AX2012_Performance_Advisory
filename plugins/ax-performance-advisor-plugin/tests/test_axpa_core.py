import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from axpa_core import analyze_evidence, batch_collision_summary, build_report, compare_baseline, export_evidence_pack, export_powerbi_dataset, load_evidence
from ai_insights import AI_FEATURES, generate_ai_insights, render_markdown
from realization_pack import generate_realization_pack
from admin_execution import build_execution_plan
from enterprise_observability import generate_enterprise_pack
from rag_qa import build_index, answer
from advanced_usps import generate_advanced_usps
from governance_extensions import generate_governance_extensions
from strategy_extensions import generate_strategy_extensions
from ai_ki_extensions import generate_ai_ki_extensions
from market_differentiators import generate_market_differentiators
from learning_extensions import generate_learning_extensions
from autonomous_intelligence import generate_autonomous_intelligence
from autonomous_ops import generate_autonomous_ops
from evidence_health import generate_evidence_health
from skill_catalog import generate_skill_catalog
from compare_environments import compare_environments
from ax_live_blocking_intelligence import generate_ax_live_blocking_intelligence
from platform_extensions import generate_platform_extensions
from qa_dashboard_http import run_http_check, find_free_port
from check_scheduler_health import assess as assess_scheduler
from validate_push_readiness import build as build_push_readiness
from collect_operational_status import collect as collect_operational_status
from flight_recorder import build_report as build_flight_recorder_report, write_feedback
from user_client_impact_radar import generate_user_client_impact_radar
from frontend_user_usps import generate_frontend_user_usps
from ceo_cockpit import generate_ceo_cockpit
from mcp_server import handle


class AxpaCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.evidence = PLUGIN_ROOT / "sample" / "evidence"
        self.tmp = Path(tempfile.mkdtemp(prefix="axpa-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_analyze_sample_evidence_generates_findings(self) -> None:
        findings = analyze_evidence(self.evidence)
        self.assertGreaterEqual(len(findings), 10)
        titles = {item["title"] for item in findings}
        self.assertTrue(any("Batch SLA risk" in title for title in titles))
        self.assertTrue(any("Environment drift" in title for title in titles))
        self.assertTrue(any("Data growth pressure" in title for title in titles))
        self.assertTrue(any("TempDB pressure" in title for title in titles))
        self.assertTrue(any("Parameter-sensitive plan" in title for title in titles))
        self.assertTrue(any("Deadlock evidence" in title for title in titles))
        self.assertTrue(any("AIF/service" in title for title in titles))

    def test_report_contains_management_sections(self) -> None:
        report = build_report(self.evidence)
        self.assertIn("Executive Summary", report)
        self.assertIn("Performance debt items", report)
        self.assertIn("Top Findings", report)

    def test_exports_write_files(self) -> None:
        pack = export_evidence_pack(self.evidence, self.tmp / "pack.zip")
        dataset = export_powerbi_dataset(self.evidence, self.tmp / "powerbi.csv")
        self.assertTrue(pack.exists())
        self.assertGreater(pack.stat().st_size, 0)
        self.assertTrue(dataset.exists())
        self.assertIn("severity", dataset.read_text(encoding="utf-8"))

    def test_compare_baseline_returns_result(self) -> None:
        result = compare_baseline(self.evidence, self.evidence)
        self.assertEqual(result["result"], "unchanged")
        self.assertEqual(result["beforeRiskScore"], result["afterRiskScore"])

    def test_mcp_tool_list_and_call(self) -> None:
        listed = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(listed["id"], 1)
        self.assertGreaterEqual(len(listed["result"]["tools"]), 4)
        called = handle({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "analyze_evidence",
                "arguments": {"evidence": str(self.evidence)},
            },
        })
        payload = json.loads(called["result"]["content"][0]["text"])
        self.assertGreaterEqual(len(payload), 10)

    def test_mcp_ticket_export(self) -> None:
        output = self.tmp / "tickets.csv"
        called = handle({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "export_ticket_backlog",
                "arguments": {"evidence": str(self.evidence), "output": str(output), "system": "azure-devops"},
            },
        })
        self.assertEqual(called["id"], 3)
        self.assertTrue(output.exists())
        self.assertIn("Acceptance Criteria", output.read_text(encoding="utf-8"))

    def test_ai_insights_generate_all_twenty_features(self) -> None:
        payload = generate_ai_insights(self.evidence, "Warum war AX langsam?")
        self.assertEqual(payload["metadata"]["featureCount"], 20)
        self.assertEqual(len(AI_FEATURES), 20)
        required = {
            "naturalLanguageRootCauseChat",
            "findingExplainers",
            "changeRiskPredictor",
            "batchSchedulerOptimizer",
            "queryToAxCodeMapping",
            "regressionDetector",
            "remediationPlanner",
            "evidenceGapDetector",
            "incidentSummary",
            "gxpValidationAssistant",
            "runbookCopilot",
            "noiseReduction",
            "businessImpactEstimator",
            "knowledgeBaseLearning",
            "anomalyForecasting",
            "d365MigrationSignal",
            "ticketAutoDrafting",
            "executiveNarrative",
            "sqlPlanInterpreter",
            "safeActionClassifier",
        }
        self.assertTrue(required.issubset(payload.keys()))
        self.assertGreater(payload["metadata"]["findingCount"], 0)
        self.assertIn("Warum war AX langsam?", payload["naturalLanguageRootCauseChat"]["question"])
        self.assertIn("AI/KI Performance Advisory Pack", render_markdown(payload))

    def test_mcp_ai_insights_export(self) -> None:
        output = self.tmp / "ai-insights.json"
        called = handle({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "generate_ai_insights",
                "arguments": {"evidence": str(self.evidence), "output": str(output), "question": "Warum war AX langsam?"},
            },
        })
        self.assertEqual(called["id"], 4)
        self.assertTrue(output.exists())
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["metadata"]["featureCount"], 20)

    def test_realization_pack_closes_prepared_features(self) -> None:
        payload = generate_realization_pack(self.evidence)
        self.assertIn("evidenceTrustScore", payload)
        self.assertIn("collectorFixSuggestions", payload)
        self.assertIn("roleBasedBriefings", payload)
        self.assertIn("dynamicSlaContracts", payload)
        self.assertIn("syntheticLoadReplayPlan", payload)
        self.assertIn("closedLoopGovernance", payload)
        self.assertIn("adapterReadiness", payload)
        self.assertIn("sql2016EndOfSupportRisk", payload)
        self.assertGreaterEqual(payload["evidenceTrustScore"]["score"], 0)
        self.assertIn("llmChat", payload["adapterReadiness"])

    def test_admin_execution_plan_is_guarded_preview(self) -> None:
        out = self.tmp / "admin"
        payload = build_execution_plan(self.evidence, out, "TEST", "high")
        self.assertGreater(payload["actionCount"], 0)
        self.assertEqual(payload["executableCount"], 0)
        self.assertTrue((out / "admin-execution-plan.json").exists())
        self.assertTrue((out / "audit" / "admin-execution-audit.json").exists())
        first = payload["actions"][0]
        self.assertEqual(first["status"], "preview-only")
        self.assertIn("confirmationToken", first)
        self.assertTrue(Path(first["script"]).exists())

    def test_enterprise_observability_pack_outputs_platform_features(self) -> None:
        out = self.tmp / "enterprise"
        payload = generate_enterprise_pack(self.evidence, out, [str(self.evidence)])
        self.assertIn("timeSeriesStore", payload)
        self.assertIn("alerts", payload)
        self.assertIn("estateInventory", payload)
        self.assertIn("planRepository", payload)
        self.assertIn("notifications", payload)
        self.assertTrue((out / "axpa-trends.sqlite").exists())
        self.assertTrue((out / "enterprise-observability-pack.json").exists())
        self.assertTrue((out / "notifications" / "teams-card.json").exists())

    def test_local_rag_qa_returns_sources(self) -> None:
        index = build_index(self.evidence)
        result = answer(index, "blocking batch query")
        self.assertGreater(index["docCount"], 0)
        self.assertIn("sources", result)

    def test_advanced_usps_generate_operational_pack(self) -> None:
        payload = generate_advanced_usps(self.evidence)
        self.assertIn("sloBurnRate", payload)
        self.assertIn("maintenanceWindowOptimizer", payload)
        self.assertIn("costOfDelay", payload)
        self.assertIn("releaseGate", payload)
        self.assertIn("retentionCandidates", payload)
        self.assertIn("knownIssueMatches", payload)
        self.assertIn("executiveBriefings", payload)
        self.assertIn("temporalHotspotMap", payload)
        self.assertIn("workloadFingerprinting", payload)
        self.assertIn("archiveImpactSandbox", payload)
        self.assertIn("performanceBudgeting", payload)
        self.assertIn("validationOrchestrator", payload)
        self.assertIn("operatorCopilotContext", payload)
        self.assertIn("selfCalibratingThresholds", payload)
        self.assertIn("budgets", payload["performanceBudgeting"])

    def test_governance_extensions_generate_audit_outputs(self) -> None:
        out = self.tmp / "governance"
        payload = generate_governance_extensions(self.evidence, out)
        self.assertIn("runbookAutomation", payload)
        self.assertIn("raciMatrix", payload)
        self.assertIn("businessImpactTimeline", payload)
        self.assertIn("suppressionGovernance", payload)
        self.assertIn("dataQualityChecks", payload)
        self.assertTrue(Path(payload["auditExport"]["csv"]).exists())

    def test_strategy_extensions_generate_decision_views(self) -> None:
        payload = generate_strategy_extensions(self.evidence)
        self.assertIn("whatIfSimulation", payload)
        self.assertIn("baselineBenchmark", payload)
        self.assertIn("evidenceCompletenessRoadmap", payload)
        self.assertIn("remediationKanban", payload)
        self.assertIn("kpiContracts", payload)
        self.assertIn("capabilityMatrix", payload)

    def test_ai_ki_extensions_generate_context_artifacts(self) -> None:
        payload = generate_ai_ki_extensions(self.evidence)
        self.assertIn("hypothesisRanking", payload)
        self.assertIn("counterfactuals", payload)
        self.assertIn("causalNarrative", payload)
        self.assertIn("llmContextPack", payload)
        self.assertIn("evidenceChunks", payload)
        self.assertIn("confidenceCalibration", payload)
        self.assertIn("batchRescheduleSimulator", payload)
        self.assertIn("rootCauseBridge", payload)
        self.assertIn("nextBestEvidence", payload)
        self.assertIn("changeRoiPrioritizer", payload)
        self.assertIn("adminCopilotQuestions", payload)
        self.assertGreater(len(payload["evidenceChunks"]), 0)

    def test_market_differentiators_generate_more_usps(self) -> None:
        payload = generate_market_differentiators(self.evidence)
        self.assertIn("vendorNeutralComparison", payload)
        self.assertIn("migrationReadiness", payload)
        self.assertIn("resilienceScore", payload)
        self.assertIn("knowledgeGraph", payload)
        self.assertIn("processOwnerScorecards", payload)
        self.assertIn("evidenceMarketplace", payload)
        self.assertIn("valueRealization", payload)
        self.assertIn("performanceDigitalTwin", payload)
        self.assertIn("causalGraphEngine", payload)
        self.assertIn("performanceContractTests", payload)
        self.assertIn("changeBlastRadius", payload)
        self.assertIn("performanceDebtInterest", payload)
        self.assertIn("remediationPortfolioOptimizer", payload)
        self.assertIn("axAgingRiskIndex", payload)
        self.assertIn("regressionTestSkeletons", payload)
        self.assertGreaterEqual(payload["performanceDigitalTwin"]["nodeCount"], 1)
        self.assertGreaterEqual(payload["performanceContractTests"]["contractCount"], 1)

    def test_learning_extensions_generate_ai_decision_artifacts(self) -> None:
        out = self.tmp / "learning"
        payload = generate_learning_extensions(self.evidence, out)
        self.assertIn("recommendationMemory", payload)
        self.assertIn("similaritySearch", payload)
        self.assertIn("acceptanceSimulation", payload)
        self.assertIn("executiveNarrativeVariants", payload)
        self.assertIn("anomalyExplanation", payload)
        self.assertIn("actionConfidenceTuning", payload)
        self.assertTrue((out / "recommendation-memory.sqlite").exists())

    def test_autonomous_intelligence_generate_ai_usp_artifacts(self) -> None:
        payload = generate_autonomous_intelligence(self.evidence)
        self.assertIn("evidenceScout", payload)
        self.assertIn("investigationTree", payload)
        self.assertIn("rootCauseDebate", payload)
        self.assertIn("recommendationQualityGate", payload)
        self.assertIn("kpiStoryboard", payload)
        self.assertIn("anonymizedPatternLibrary", payload)

    def test_autonomous_ops_generate_twenty_operational_features(self) -> None:
        payload = generate_autonomous_ops(self.evidence)
        self.assertEqual(payload["featureCount"], 20)
        self.assertIn("investigationQueue", payload)
        self.assertIn("followUpQuestions", payload)
        self.assertIn("evidenceAcquisitionPlanner", payload)
        self.assertIn("changeDrafts", payload)
        self.assertIn("validationRunPlanner", payload)
        self.assertIn("readinessGate", payload)
        self.assertIn("nextBestActions", payload)
        self.assertIn("executiveRiskBriefing", payload)
        self.assertGreater(len(payload["investigationQueue"]), 0)
        self.assertGreater(len(payload["evidenceAcquisitionPlanner"]["tasks"]), 0)

    def test_operational_gap_features_generate_real_payloads(self) -> None:
        health = generate_evidence_health(self.evidence)
        catalog = generate_skill_catalog(PLUGIN_ROOT)
        comparison = compare_environments([self.evidence])
        self.assertIn("sources", health)
        self.assertGreater(health["summary"]["total"], 0)
        self.assertGreaterEqual(catalog["skillCount"], 1)
        self.assertIn("Primary", catalog["groups"])
        self.assertEqual(comparison["environmentCount"], 1)

    def test_ax_live_blocking_intelligence_detects_blocked_ax_workers(self) -> None:
        shutil.copytree(self.evidence, self.tmp / "evidence")
        evidence = self.tmp / "evidence"
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "dbl10945,BRAS3333,223,391,Microsoft Dynamics AX,running,MicrosoftDynamicsGBLAX,UPDATE,LCK_M_U,314283,10,314283,0,10,2000,\"UPDATE GENERALJOURNALACCOUNTENTRY SET ISCREDIT=@P1 WHERE EXISTS (SELECT 'x' FROM GENERALJOURNALENTRY T2 WHERE T2.TRANSFERID=@P17)\",2026-04-24T09:00:03+02:00,AX,Worker-Blocked,Wird beendet - Blockiert\n"
            "dbl80448,BRAS3333,132,,Microsoft Dynamics AX,running,MicrosoftDynamicsGBLAX,SELECT,,189073,10,189073,100,0,3000,\"SELECT SUM(T1.POSTEDQTY) FROM INVENTSUM T1 WHERE EXISTS (SELECT 'x' FROM INVENTDIM T2 WHERE T2.INVENTDIMID=T1.INVENTDIMID)\",2026-04-24T09:00:03+02:00,AX,Worker,Wird beendet - Blockiert\n",
            encoding="utf-8",
        )
        findings = analyze_evidence(evidence)
        payload = generate_ax_live_blocking_intelligence(evidence)
        self.assertTrue(any("AX worker blocked session" in f["title"] for f in findings))
        self.assertEqual(payload["featureCount"], 10)
        self.assertEqual(payload["blockedRows"], 1)
        self.assertTrue(any(item["table"] == "GENERALJOURNALACCOUNTENTRY" for item in payload["criticalQueryClassifier"]))
        self.assertTrue(any(item["table"] == "GENERALJOURNALACCOUNTENTRY" for item in payload["hotTableContention"]))

    def test_batch_collision_analysis_detects_overlaps_and_storms(self) -> None:
        shutil.copytree(self.evidence, self.tmp / "evidence")
        evidence = self.tmp / "evidence"
        (evidence / "batch_tasks.csv").write_text(
            "task_id,job_id,class_number,caption,batch_group,company,status,start_time,end_time,duration_seconds\n"
            "1,10,100,Inventory close,INVENT,GBL,4,27.04.2026 02:00:00,27.04.2026 02:45:00,2700\n"
            "2,11,101,MRP run,MRP,GBL,4,27.04.2026 02:10:00,27.04.2026 02:50:00,2400\n"
            "3,12,102,AIF import,AIF,GBL,4,27.04.2026 02:15:00,27.04.2026 02:20:00,300\n"
            "4,13,103,Tiny 1,LOG2,GBL,4,27.04.2026 03:00:01,27.04.2026 03:00:05,4\n"
            "5,14,104,Tiny 2,LOG2,GBL,4,27.04.2026 03:00:02,27.04.2026 03:00:05,3\n"
            "6,15,105,Tiny 3,LOG2,GBL,4,27.04.2026 03:00:03,27.04.2026 03:00:05,2\n"
            "7,16,106,Tiny 4,LOG2,GBL,4,27.04.2026 03:00:04,27.04.2026 03:00:06,2\n"
            "8,17,107,Tiny 5,LOG2,GBL,4,27.04.2026 03:00:05,27.04.2026 03:00:07,2\n",
            encoding="utf-8",
        )
        summary = batch_collision_summary(load_evidence(evidence))
        findings = analyze_evidence(evidence)
        self.assertGreaterEqual(summary["collisionCount"], 2)
        self.assertGreaterEqual(summary["peakConcurrency"], 2)
        self.assertTrue(summary["shortRunnerStorms"])
        self.assertTrue(any("AX batch group collision" in f["title"] or "AX short-running batch storm" in f["title"] for f in findings))

    def test_batch_collision_summary_keeps_live_blocked_rows_without_batch_intervals(self) -> None:
        evidence = self.tmp / "evidence-no-batch-intervals"
        evidence.mkdir()
        (evidence / "batch_tasks.csv").write_text(
            "task_id,job_id,class_number,caption,batch_group,company,status,start_time,end_time,duration_seconds\n"
            "1,10,100,No end,INVENT,GBL,4,2026-05-11 14:00:00,,0\n",
            encoding="utf-8",
        )
        (evidence / "ax_live_blocking.csv").write_text(
            "session_id,blocking_session_id,program_name,statement_text\n"
            "12,99,Microsoft Dynamics AX,SELECT 1\n",
            encoding="utf-8",
        )

        summary = batch_collision_summary(load_evidence(evidence))

        self.assertEqual(summary["taskCount"], 0)
        self.assertEqual(summary["liveBlockedRows"], 1)

    def test_pipeline_orchestrator_analyze_only_writes_manifest(self) -> None:
        evidence = self.tmp / "evidence"
        out = self.tmp / "out"
        shutil.copytree(self.evidence, evidence)
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "run_axpa_pipeline.py"),
                "--environment",
                "unit",
                "--server",
                "unit-sql",
                "--database",
                "unit-ax",
                "--evidence",
                str(evidence),
                "--out",
                str(out),
            ],
            cwd=str(PLUGIN_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "unit-pipeline-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "ok")
        self.assertTrue((out / "unit-dashboard.html").exists())
        self.assertTrue(any(step["name"] == "trend-store" and step["status"] == "ok" for step in manifest["steps"]))
        dashboard_step = next(step for step in manifest["steps"] if step["name"] == "dashboard")
        self.assertIn(str(evidence.resolve()), dashboard_step["command"])
        self.assertIn(str((out / "unit-dashboard.html").resolve()), dashboard_step["command"])
        self.assertFalse((out / "unit.lock").exists())

    def test_pipeline_orchestrator_normalizes_relative_evidence_paths(self) -> None:
        evidence = self.tmp / "relative-evidence"
        shutil.copytree(self.evidence, evidence)
        out = self.tmp / "relative-out"
        repo_root = PLUGIN_ROOT.parents[1]
        relative_evidence = Path(os.path.relpath(evidence, repo_root))
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "run_axpa_pipeline.py"),
                "--environment",
                "relative-unit",
                "--server",
                "unit-sql",
                "--database",
                "unit-ax",
                "--evidence",
                str(relative_evidence),
                "--out",
                str(out),
            ],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((out / "relative-unit-pipeline-manifest.json").read_text(encoding="utf-8"))
        analyze_step = next(step for step in manifest["steps"] if step["name"] == "analyze")
        self.assertIn(str((repo_root / relative_evidence).resolve()), analyze_step["command"])
        self.assertTrue((out / "relative-unit-dashboard.html").exists())

    def test_platform_extensions_cover_product_gaps(self) -> None:
        out = self.tmp / "platform"
        payload = generate_platform_extensions(self.evidence, out)
        for key in [
            "operatorCockpit",
            "safetyGuard",
            "batchControlTower",
            "attributionEngine",
            "dailyProductionLoop",
            "userClientImpactRadar",
            "ceoCockpit",
            "trendDashboard",
            "recommendationLifecycle",
            "incidentReplay",
            "queryPlanDiff",
            "deadlockGraph",
            "aosTopology",
            "schedulerHardening",
            "productivePushReadiness",
            "xppAttribution",
            "environmentDriftGuard",
            "aiDecisionCockpit",
            "liveBatchCollisionWatch",
            "batchRescheduleCalendar",
            "sqlBlockingChainRecorder",
            "axBusinessProcessSla",
            "evidenceGapAssistant",
            "deploymentRegressionGuard",
            "adminRemediationWorkbench",
            "alertingRules",
            "aiSafeFeatures",
            "yoloWaveUspPack",
        ]:
            self.assertIn(key, payload)
        self.assertTrue((out / "platform-extensions.json").exists())
        self.assertGreaterEqual(payload["recommendationLifecycle"]["items"].__len__(), 1)
        self.assertIn("topSuspect", payload["operatorCockpit"])
        self.assertEqual(payload["safetyGuard"]["collectorMode"], "read-only")
        self.assertIn("moveCandidates", payload["batchControlTower"])
        self.assertIn("items", payload["attributionEngine"])
        self.assertTrue(payload["dailyProductionLoop"]["localAnalysisAllowed"])
        self.assertEqual(payload["userClientImpactRadar"]["mode"], "internal-full-detail")
        self.assertEqual(payload["ceoCockpit"]["featureCount"], 15)
        self.assertEqual(payload["ceoCockpit"]["writePolicy"], "local-files-only-no-db-writes")
        self.assertIn("accepted", payload["recommendationLifecycle"]["transitions"]["proposed"])
        self.assertIn("mapperInputs", payload["xppAttribution"])
        self.assertIn("dimensions", payload["environmentDriftGuard"])
        self.assertIn("alerts", payload["liveBatchCollisionWatch"])
        self.assertIn("proposals", payload["batchRescheduleCalendar"])
        self.assertIn("chains", payload["sqlBlockingChainRecorder"])
        self.assertIn("items", payload["axBusinessProcessSla"])
        self.assertIn("gaps", payload["evidenceGapAssistant"])
        self.assertIn("topRuntimeQueries", payload["deploymentRegressionGuard"])
        self.assertIn("actions", payload["adminRemediationWorkbench"])
        self.assertIn("rules", payload["alertingRules"])
        self.assertIn("batchTwin", payload["aiSafeFeatures"])
        self.assertIn("axFixFeasibilityScore", payload["yoloWaveUspPack"])

    def test_safety_guard_detects_read_only_and_risky_permissions(self) -> None:
        from safety_guard import generate_safety_guard

        evidence = self.tmp / "evidence-safety"
        scripts_dir = self.tmp / "scripts-safety"
        out = self.tmp / "out-safety"
        evidence.mkdir()
        scripts_dir.mkdir()
        (scripts_dir / "collect_readonly.ps1").write_text(
            "Invoke-AxpaSqlQuery -Query @\"\nSELECT TOP (10) * FROM sys.dm_exec_requests;\n\"@\n",
            encoding="utf-8",
        )
        (evidence / "permissions.csv").write_text(
            '"permission","value"\n"connect","1"\n"view_server_state","1"\n"can_create_table","1"\n"can_alter_any_schema","0"\n',
            encoding="utf-8",
        )

        payload = generate_safety_guard(evidence, scripts_dir, out)

        self.assertEqual(payload["verdict"], "amber")
        self.assertEqual(payload["collectorMode"], "read-only")
        self.assertIn("can_create_table", payload["riskyPermissions"])
        self.assertTrue((out / "safety-guard.json").exists())

    def test_safety_guard_blocks_write_verbs(self) -> None:
        from safety_guard import generate_safety_guard

        evidence = self.tmp / "evidence-safety-write"
        scripts_dir = self.tmp / "scripts-safety-write"
        out = self.tmp / "out-safety-write"
        evidence.mkdir()
        scripts_dir.mkdir()
        (scripts_dir / "collect_bad.ps1").write_text(
            "Invoke-AxpaSqlQuery -Query @\"\nUPDATE dbo.BATCH SET STATUS = 1;\n\"@\n",
            encoding="utf-8",
        )

        payload = generate_safety_guard(evidence, scripts_dir, out)

        self.assertEqual(payload["verdict"], "red")
        self.assertEqual(payload["collectorMode"], "blocked")
        self.assertEqual(payload["writeVerbHits"][0]["verb"], "UPDATE")

    def test_operator_cockpit_prioritizes_top_suspect_and_safe_actions(self) -> None:
        from operator_cockpit import generate_operator_cockpit

        findings = [
            {
                "id": "AXPA-1",
                "title": "AX frontend machine-impact inventory query on INVENTSUM",
                "severity": "critical",
                "confidence": "medium",
                "classification": "frontend-machine-impact",
                "axContext": {"module": "Inventory", "tables": ["INVENTSUM"], "aos": ["BRAS3333"]},
                "recommendation": {"playbook": "ax-frontend-machine-impact", "summary": "Narrow the inventory inquiry."},
                "evidence": [{"source": "sql_top_queries", "metric": "reads", "value": 1000}],
                "frontendContext": {"user": "DOMAINT\\adminsysmgmt", "host": "BRAS3333", "sessionId": "625"},
            }
        ]
        safety = {"verdict": "amber", "riskyPermissions": ["can_create_table"], "databaseWritesAllowed": False}
        payload = generate_operator_cockpit(findings, safety, {"score": 70}, {"status": "red"})

        self.assertEqual(payload["topSuspect"]["findingId"], "AXPA-1")
        self.assertEqual(payload["topSuspect"]["module"], "Inventory")
        self.assertIn("DOMAINT\\adminsysmgmt", payload["affectedContext"]["users"])
        self.assertTrue(payload["safeNextActions"])
        self.assertTrue(payload["doNotDo"])
        self.assertEqual(payload["safetyVerdict"], "amber")

    def test_batch_control_tower_builds_move_candidates(self) -> None:
        from batch_control_tower import generate_batch_control_tower

        evidence = self.tmp / "evidence-batch-tower"
        evidence.mkdir()
        (evidence / "batch_tasks.csv").write_text(
            "task_id,job_id,class_number,caption,batch_group,company,status,start_time,end_time,duration_seconds\n"
            "1,1,10,MRP A,MRP,GBL,4,2026-05-11 15:00:00,2026-05-11 16:00:00,3600\n"
            "2,2,11,MRP B,MRP,GBL,4,2026-05-11 15:05:00,2026-05-11 16:05:00,3600\n"
            "3,3,12,Report A,Reports,GBL,4,2026-05-11 16:00:00,2026-05-11 16:05:00,300\n",
            encoding="utf-8",
        )

        payload = generate_batch_control_tower(evidence)

        self.assertGreaterEqual(payload["taskCount"], 3)
        self.assertTrue(payload["moveCandidates"])
        self.assertIn("validation", payload["moveCandidates"][0])
        self.assertIn("rollback", payload["moveCandidates"][0])

    def test_attribution_engine_separates_observed_inferred_and_missing_proof(self) -> None:
        from attribution_engine import generate_attribution_engine

        findings = [
            {
                "id": "AXPA-INV",
                "title": "AX frontend machine-impact inventory query on INVENTSUM",
                "severity": "critical",
                "sqlContext": {"queryHash": "0x1", "objects": ["INVENTSUM", "INVENTDIM"]},
                "axContext": {"module": "Inventory", "tables": ["INVENTSUM", "INVENTDIM"]},
            }
        ]
        evidence = self.tmp / "evidence-attribution"
        evidence.mkdir()
        payload = generate_attribution_engine(evidence, findings)

        self.assertEqual(payload["items"][0]["findingId"], "AXPA-INV")
        self.assertIn("INVENTSUM", payload["items"][0]["observed"]["tables"])
        self.assertEqual(payload["items"][0]["inferred"]["form"], "InventOnHand")
        self.assertIn("trace_parser.csv", payload["items"][0]["missingProof"])

    def test_daily_production_loop_summarizes_operational_status_without_push(self) -> None:
        from daily_production_loop import generate_daily_production_loop

        out = self.tmp / "out-daily"
        out.mkdir()
        (out / "run-operational-status.json").write_text(
            json.dumps(
                {
                    "status": "red",
                    "blockers": ["push"],
                    "components": {
                        "scheduler": {"status": "amber", "summary": "manifest=ok task=missing"},
                        "push": {"status": "red", "summary": "readyTargets=0/5"},
                        "dashboardHttpQa": {"status": "green", "summary": "http=200 ok=True"},
                    },
                }
            ),
            encoding="utf-8",
        )

        payload = generate_daily_production_loop(out, "run")

        self.assertEqual(payload["status"], "red")
        self.assertIn("push", payload["blockers"])
        self.assertTrue(payload["localAnalysisAllowed"])
        self.assertTrue((out / "run-daily-production-loop.md").exists())

    def test_platform_gap_closure_covers_remaining_ten_features(self) -> None:
        out = self.tmp / "platform-gaps"
        payload = generate_platform_extensions(self.evidence, out)
        gaps = payload["gapClosure"]
        required = {
            "deadlockCapture",
            "xppTraceAttribution",
            "retailLoadStatus",
            "productivePushExecution",
            "adminExecutionGate",
            "schedulerInstall",
            "trendRunQuality",
            "batchDependencyAwareReschedule",
            "llmRagCopilot",
            "githubReleaseReadiness",
        }
        self.assertEqual(set(gaps), required)
        self.assertIn("collectorCommand", gaps["deadlockCapture"])
        self.assertIn("dependencies", gaps["batchDependencyAwareReschedule"])
        self.assertIn("dryRunCommand", gaps["productivePushExecution"])
        self.assertIn("installCommand", gaps["schedulerInstall"])
        self.assertIn("quality", gaps["trendRunQuality"])
        self.assertIn("releaseChecklist", gaps["githubReleaseReadiness"])

    def test_gap_closure_writes_action_pack_and_references_real_scripts(self) -> None:
        out = self.tmp / "platform-gap-actions"
        payload = generate_platform_extensions(self.evidence, out)
        gaps = payload["gapClosure"]
        self.assertTrue((out / "gap-closure-actions.json").exists())
        self.assertTrue((out / "gap-closure-actions.md").exists())
        action_text = (out / "gap-closure-actions.md").read_text(encoding="utf-8")
        self.assertIn("Deadlock capture", action_text)
        self.assertIn("scripts/setup_deadlock_capture.sql", action_text)
        self.assertIn("scripts/install_windows_task.ps1", action_text)
        self.assertIn("scripts/push_integrations.py", action_text)
        self.assertTrue((SCRIPTS / "setup_deadlock_capture.sql").exists())
        self.assertTrue((SCRIPTS / "install_windows_task.ps1").exists())
        self.assertIn("setup_deadlock_capture.sql", gaps["deadlockCapture"]["collectorCommand"])
        self.assertIn("install_windows_task.ps1", gaps["schedulerInstall"]["installCommand"])

    def test_batch_dependency_graph_finds_job_chains_and_reschedule_risks(self) -> None:
        evidence = self.tmp / "batch-deps"
        shutil.copytree(self.evidence, evidence)
        (evidence / "batch_jobs.csv").write_text(
            "job_id,job_name,class_name,batch_group,aos,company,status,start_time,end_time,duration_seconds,sla_target_seconds\n"
            "100,Nightly inventory,,INVENT,,GBL,4,27.04.2026 02:00:00,27.04.2026 02:50:00,3000,3600\n"
            "200,Report wave,,Reports,,GBL,4,27.04.2026 16:00:00,27.04.2026 16:30:00,1800,1800\n",
            encoding="utf-8",
        )
        (evidence / "batch_tasks.csv").write_text(
            "task_id,job_id,class_number,caption,batch_group,company,status,start_time,end_time,duration_seconds\n"
            "1,100,10,Invent close step 1,INVENT,GBL,4,27.04.2026 02:00:00,27.04.2026 02:20:00,1200\n"
            "2,100,11,MRP dependent step,MRP,GBL,4,27.04.2026 02:21:00,27.04.2026 02:45:00,1440\n"
            "3,200,20,Report extract,Reports,GBL,4,27.04.2026 16:00:00,27.04.2026 16:05:00,300\n"
            "4,200,21,Report mail,Reports,GBL,4,27.04.2026 16:06:00,27.04.2026 16:08:00,120\n",
            encoding="utf-8",
        )
        payload = generate_platform_extensions(evidence, self.tmp / "batch-deps-out")
        graph = payload["batchDependencyGraph"]
        self.assertGreaterEqual(graph["chainCount"], 2)
        self.assertTrue(any(edge["fromGroup"] == "INVENT" and edge["toGroup"] == "MRP" for edge in graph["edges"]))
        self.assertTrue(any(chain["jobId"] == "100" and chain["risk"] in {"high", "medium"} for chain in graph["chains"]))
        self.assertTrue(any(risk["moveGroup"] == "INVENT" and "MRP" in risk["dependentGroups"] for risk in graph["rescheduleRisks"]))

    def test_strategic_usp_pack_contains_all_ten_named_features(self) -> None:
        payload = generate_platform_extensions(self.evidence, self.tmp / "strategic-usps")
        pack = payload["strategicUspPack"]
        required = {
            "batchDependencyGraph",
            "batchSlaContractManager",
            "deadlockToAxProcessAttribution",
            "aosAffinityAdvisor",
            "dataGrowthArchivingRoi",
            "changeSimulationQueue",
            "evidenceSla",
            "knownIssueMatcher",
            "operationalMaturityScore",
            "d365MigrationSignalDashboard",
        }
        self.assertEqual(set(pack), required)
        self.assertIn("contracts", pack["batchSlaContractManager"])
        self.assertIn("recommendations", pack["aosAffinityAdvisor"])
        self.assertIn("candidates", pack["dataGrowthArchivingRoi"])
        self.assertIn("simulations", pack["changeSimulationQueue"])
        self.assertIn("score", pack["evidenceSla"])
        self.assertIn("matches", pack["knownIssueMatcher"])
        self.assertIn("score", pack["operationalMaturityScore"])
        self.assertIn("decision", pack["d365MigrationSignalDashboard"])

    def test_yolo_wave_usp_pack_contains_all_twenty_features(self) -> None:
        payload = generate_platform_extensions(self.evidence, self.tmp / "yolo-wave-usps")
        pack = payload["yoloWaveUspPack"]
        required = {
            "axFixFeasibilityScore",
            "businessCalendarAwareness",
            "axTransactionCriticalityModel",
            "userExperienceCorrelation",
            "axCustomizationHotspotRanking",
            "dataRetentionPolicySimulator",
            "queryIntentClassifier",
            "operationalPlaybookGenerator",
            "axReleaseHotfixIntelligence",
            "executiveRiskToMoneyView",
            "aiWhatChangedAnalyst",
            "aiBatchNegotiator",
            "aiEvidenceLawyer",
            "aiRemediationSequencer",
            "aiFalsePositiveReducer",
            "performanceDebtRegister",
            "performanceContractTests",
            "environmentReadinessScore",
            "safeAdminExecutionCockpit",
            "axSurvivalHorizon",
        }
        self.assertEqual(set(pack), required)
        self.assertIn("items", pack["axFixFeasibilityScore"])
        self.assertIn("hourlyBatchLoad", pack["businessCalendarAwareness"])
        self.assertIn("processes", pack["axTransactionCriticalityModel"])
        self.assertIn("topHosts", pack["userExperienceCorrelation"])
        self.assertIn("candidates", pack["dataRetentionPolicySimulator"])
        self.assertIn("intentCounts", pack["queryIntentClassifier"])
        self.assertIn("playbooks", pack["operationalPlaybookGenerator"])
        self.assertIn("estimatedCostHighEur", pack["executiveRiskToMoneyView"])
        self.assertIn("negotiations", pack["aiBatchNegotiator"])
        self.assertIn("waves", pack["aiRemediationSequencer"])
        self.assertIn("debtCount", pack["performanceDebtRegister"])
        self.assertIn("contracts", pack["performanceContractTests"])
        self.assertIn("score", pack["environmentReadinessScore"])
        self.assertIn("gates", pack["safeAdminExecutionCockpit"])
        self.assertIn("estimatedWeeks", pack["axSurvivalHorizon"])

    def test_recommendation_lifecycle_cli_persists_state(self) -> None:
        state_file = self.tmp / "lifecycle.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "manage_recommendation_lifecycle.py"),
                "--state-file",
                str(state_file),
                "--finding-id",
                "AXPA-1",
                "--state",
                "accepted",
                "--actor",
                "unit",
                "--note",
                "test",
            ],
            cwd=str(PLUGIN_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        self.assertEqual(payload["items"]["AXPA-1"]["state"], "accepted")
        self.assertEqual(payload["audit"][0]["to"], "accepted")

    def test_push_integrations_dry_run_writes_audit_and_dedupes(self) -> None:
        audit = self.tmp / "push.sqlite"
        command = [
            sys.executable,
            str(SCRIPTS / "push_integrations.py"),
            "--evidence",
            str(self.evidence),
            "--targets",
            "teams,ado,jira,servicenow,powerbi",
            "--audit-db",
            str(audit),
            "--limit",
            "2",
            "--dry-run",
        ]
        first = subprocess.run(command, cwd=str(PLUGIN_ROOT), text=True, capture_output=True)
        second = subprocess.run(command, cwd=str(PLUGIN_ROOT), text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue(audit.exists())
        self.assertIn("duplicate-skipped", second.stdout)

    def test_dashboard_http_qa_serves_dashboard_without_file_url(self) -> None:
        dashboard = self.tmp / "out" / "unit-dashboard.html"
        dashboard.parent.mkdir(parents=True)
        dashboard.write_text("<html><body>AX Performance Advisor Dashboard Platform YOLO Wave USP Pack AX Survival Horizon</body></html>", encoding="utf-8")
        result = run_http_check(self.tmp, dashboard, find_free_port(8900), ["YOLO Wave USP Pack", "AX Survival Horizon"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], 200)

    def test_production_readiness_pack_cli_writes_commands(self) -> None:
        output = self.tmp / "production-readiness.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "build_production_readiness_pack.py"),
                "--environment",
                "unit",
                "--server",
                "unit-sql",
                "--database",
                "unit-ax",
                "--evidence",
                str(self.evidence),
                "--out",
                str(self.tmp / "out"),
                "--output",
                str(output),
            ],
            cwd=str(PLUGIN_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("dashboardHttpQa", payload["steps"])
        self.assertIn("scheduler", payload["steps"])
        self.assertIn("traceAttribution", payload["steps"])
        self.assertIn("productivePush", payload["steps"])
        self.assertIn("adminExecutionGate", payload["steps"])
        self.assertIn("healthcheck", payload["steps"]["scheduler"])
        self.assertIn("preflight", payload["steps"]["productivePush"])
        self.assertIn("preflight", payload["steps"]["adminExecutionGate"])

    def test_scheduler_health_assesses_manifest_and_lock(self) -> None:
        manifest = self.tmp / "manifest.json"
        manifest.write_text(json.dumps({"status": "ok", "finishedAt": "2026-05-09T00:00:00Z", "steps": [{"name": "analyze", "status": "ok"}]}), encoding="utf-8")
        payload = assess_scheduler(manifest, self.tmp / "unit.lock")
        self.assertEqual(payload["status"], "green")
        self.assertEqual(payload["manifestStatus"], "ok")

    def test_push_readiness_reports_missing_env_and_audit(self) -> None:
        payload = build_push_readiness(["teams", "ado"], self.tmp / "push.sqlite")
        self.assertIn(payload["status"], {"red", "amber"})
        self.assertEqual(payload["targetCount"], 2)
        self.assertFalse(payload["audit"]["exists"])

    def test_admin_gate_preflight_cli_writes_go_nogo(self) -> None:
        output = self.tmp / "admin-preflight.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "admin_gate_preflight.py"),
                "--evidence",
                str(self.evidence),
                "--output-dir",
                str(self.tmp / "admin-exec"),
                "--environment",
                "TEST",
                "--output",
                str(output),
            ],
            cwd=str(PLUGIN_ROOT),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("goNoGo", payload)
        self.assertIn("blockedCount", payload)

    def test_operational_status_collects_preflight_outputs(self) -> None:
        (self.tmp / "unit-scheduler-health.json").write_text(json.dumps({"status": "green", "manifestStatus": "ok", "task": {"status": "present"}}), encoding="utf-8")
        (self.tmp / "unit-push-readiness.json").write_text(json.dumps({"status": "amber", "readyTargets": 1, "targetCount": 2, "audit": {"records": 3}}), encoding="utf-8")
        (self.tmp / "unit-admin-gate-preflight.json").write_text(json.dumps({"status": "amber", "goNoGo": "NO-GO", "executableCount": 0}), encoding="utf-8")
        (self.tmp / "unit-dashboard-http-qa.json").write_text(json.dumps({"ok": True, "status": 200}), encoding="utf-8")
        (self.tmp / "unit-production-readiness-pack.json").write_text(json.dumps({"steps": {"scheduler": {}, "productivePush": {}}}), encoding="utf-8")
        payload = collect_operational_status(self.tmp, "unit")
        self.assertEqual(payload["componentCount"], 5)
        self.assertEqual(payload["components"]["scheduler"]["status"], "green")
        self.assertEqual(payload["components"]["dashboardHttpQa"]["status"], "green")
        self.assertIn(payload["status"], {"amber", "green"})

    def test_platform_extensions_include_max_usp_productization_pack(self) -> None:
        payload = generate_platform_extensions(self.evidence, self.tmp / "platform", self.tmp / "missing-trends.sqlite")
        max_pack = payload["maxUspProductizationPack"]
        self.assertEqual(max_pack["featureCount"], 20)
        self.assertIn("productizationScore", max_pack)
        self.assertIn("connectorLaunchpad", max_pack)
        self.assertIn("traceAttributionLaunchpad", max_pack)
        self.assertIn("schedulerLaunchPack", max_pack)
        self.assertGreaterEqual(len(max_pack["knowledgeBaseSeeds"]), 1)

    def test_frontend_machine_impact_detects_wide_inventory_query(self) -> None:
        evidence = self.tmp / "frontend-evidence"
        evidence.mkdir()
        (evidence / "metadata.json").write_text(json.dumps({"environment": "unit", "timeWindow": {"start": "2026-05-10T08:00:00", "end": "2026-05-10T09:00:00"}}), encoding="utf-8")
        (evidence / "sql_top_queries.csv").write_text(
            "query_hash,plan_hash,database_name,object_name,statement_text,total_cpu_ms,total_duration_ms,total_logical_reads,execution_count,avg_duration_ms,avg_logical_reads,last_execution_time\n"
            "0xINV,0xPLAN,AXDB,,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",500000,900000,250000000,3,300000,83333333,2026-05-10T08:30:00\n",
            encoding="utf-8",
        )
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "user1,AOS1,123,0,Microsoft Dynamics AX,running,AXDB,SELECT,,0,120000,180000,0,0,150000000,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",2026-05-10T08:31:00,AX,Worker,running\n",
            encoding="utf-8",
        )
        findings = analyze_evidence(evidence)
        self.assertTrue(any(f["recommendation"]["playbook"] == "ax-frontend-machine-impact" for f in findings))
        platform = generate_platform_extensions(evidence, self.tmp / "frontend-platform")
        advisor = platform["axFrontendMachineImpactAdvisor"]
        self.assertGreaterEqual(advisor["itemCount"], 1)
        self.assertEqual(advisor["topItems"][0]["inventoryTable"], "INVENTSUM")

    def test_lightweight_flight_recorder_classifies_without_trace_parser(self) -> None:
        evidence = self.tmp / "flight-evidence"
        evidence.mkdir()
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "user1,AOS1,123,0,Microsoft Dynamics AX,running,AXDB,SELECT,,0,120000,180000,0,0,150000000,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",2026-05-10T08:31:00,AX,Worker,running\n",
            encoding="utf-8",
        )
        output = self.tmp / "flight.json"
        payload = build_flight_recorder_report(evidence, output, complaint_user="user1", complaint_host="AOS1", complaint_text="inventory")
        self.assertTrue(output.exists())
        self.assertEqual(payload["wideInventoryCount"], 1)
        self.assertEqual(payload["topRows"][0]["family"], "wide-inventory-frontend")
        self.assertEqual(payload["complaintWizard"]["decision"], "wide-inventory-likely")
        self.assertIn("knownPatternLearning", payload)
        self.assertIn("formInferenceEngine", payload)
        self.assertEqual(payload["formInferenceEngine"]["top"][0]["best"]["form"], "InventOnHand")
        platform = generate_platform_extensions(evidence, self.tmp / "flight-platform")
        self.assertIn("lightweightFlightRecorder", platform)
        self.assertEqual(platform["lightweightFlightRecorder"]["wideInventoryCount"], 1)

    def test_user_client_impact_radar_lists_internal_user_and_client_impact(self) -> None:
        evidence = self.tmp / "user-client-impact"
        evidence.mkdir()
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "userA,CLIENT1,10,0,Microsoft Dynamics AX,running,AXDB,SELECT,,0,1000,5000,0,0,2000000,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",2026-05-10T08:31:00,AX,Worker,running\n"
            "userB,CLIENT2,11,10,Microsoft Dynamics AX,running,AXDB,SELECT,LCK_M_U,90000,200,95000,0,0,1000,\"SELECT * FROM CUSTTRANS WHERE ACCOUNTNUM=@P1\",2026-05-10T08:32:00,AX,Worker,blocked\n",
            encoding="utf-8",
        )
        (evidence / "user_sessions.csv").write_text(
            "user_id,client_type,status,login_time,aos,client_computer\n"
            "userA,3,1,May 11 2026 08:00AM,1,CLIENT1\n"
            "userB,3,1,May 11 2026 08:00AM,1,CLIENT2\n",
            encoding="utf-8",
        )

        output = self.tmp / "user-client-impact.json"
        payload = generate_user_client_impact_radar(evidence, output)

        self.assertTrue(output.exists())
        self.assertEqual(payload["mode"], "internal-full-detail")
        self.assertEqual(payload["writePolicy"], "local-files-only-no-db-writes")
        self.assertEqual(payload["topUsers"][0]["user"], "userA")
        self.assertEqual(payload["topUsers"][0]["role"], "possible-blocker-machine-impact")
        self.assertGreaterEqual(payload["topUsers"][0]["wideInventoryRows"], 1)
        self.assertGreaterEqual(payload["topClients"][0]["impactScore"], 1)

    def test_frontend_user_usps_generate_all_twenty_concrete_features(self) -> None:
        evidence = self.tmp / "frontend-user-usps"
        evidence.mkdir()
        (evidence / "metadata.json").write_text(json.dumps({"environment": "unit", "sqlServer": "AXSQL", "axDatabase": "AXDB"}), encoding="utf-8")
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "userA,CLIENT1,10,0,Microsoft Dynamics AX,running,AXDB,SELECT,,0,120000,180000,0,0,180000000,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",2026-05-10T08:31:00,AX,Worker,running\n"
            "userB,CLIENT2,11,10,Microsoft Dynamics AX,running,AXDB,SELECT,LCK_M_U,90000,200,95000,0,0,1000,\"SELECT * FROM CUSTTRANS WHERE ACCOUNTNUM=@P1\",2026-05-10T08:32:00,AX,Worker,blocked\n",
            encoding="utf-8",
        )
        (evidence / "user_sessions.csv").write_text(
            "user_id,client_type,status,login_time,aos,client_computer\n"
            "userA,3,1,May 11 2026 08:00AM,AOS1,CLIENT1\n"
            "userB,3,1,May 11 2026 08:00AM,AOS1,CLIENT2\n",
            encoding="utf-8",
        )
        (evidence / "sql_top_queries.csv").write_text(
            "query_hash,plan_hash,database_name,object_name,statement_text,total_cpu_ms,total_duration_ms,total_logical_reads,execution_count,avg_duration_ms,avg_logical_reads,last_execution_time\n"
            "0xINV,0xPLAN,AXDB,,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",500000,900000,250000000,3,300000,83333333,2026-05-10T08:30:00\n",
            encoding="utf-8",
        )
        (evidence / "batch_tasks.csv").write_text(
            "task_id,job_id,class_number,caption,batch_group,company,status,start_time,end_time,duration_seconds\n"
            "1,10,100,Inventory close,INVENT,GBL,4,2026-05-10T02:00:00,2026-05-10T02:45:00,2700\n",
            encoding="utf-8",
        )

        output = self.tmp / "frontend-user-usps.json"
        payload = generate_frontend_user_usps(evidence, output)

        required = {
            "axUserFrictionIndex",
            "frontendBlastRadiusRadar",
            "axFormToSqlAttribution",
            "misusePatternDetection",
            "clientHostReputationScore",
            "businessProcessHeatmap",
            "axPerformanceGuardrails",
            "smartUserCoachingPack",
            "aosDrainRecommendation",
            "criticalTableStressIndex",
            "readAmplificationDetector",
            "filterQualityAdvisor",
            "doNotRunTogetherMatrix",
            "incidentFingerprintLibrary",
            "aiEvidenceFirstTroubleshooter",
            "axSlowMorningDetector",
            "sqlToAxTableSemanticExplainer",
            "changeFreezeRiskAdvisor",
            "executiveBusinessLossEstimator",
            "axModernizationPressureIndex",
        }
        self.assertEqual(payload["featureCount"], 20)
        self.assertEqual(set(payload["features"].keys()), required)
        self.assertEqual(payload["writePolicy"], "local-files-only-no-db-writes")
        self.assertTrue(output.exists())
        self.assertGreaterEqual(payload["features"]["axUserFrictionIndex"]["topUsers"][0]["score"], 1)
        self.assertGreaterEqual(payload["features"]["frontendBlastRadiusRadar"]["blastRadiusItems"][0]["affectedUsers"], 1)
        self.assertEqual(payload["features"]["misusePatternDetection"]["patterns"][0]["pattern"], "broad-inventory-query")
        self.assertIn("InventOnHand", payload["features"]["axFormToSqlAttribution"]["items"][0]["likelyForms"])
        self.assertGreaterEqual(payload["features"]["executiveBusinessLossEstimator"]["estimatedCostHighEur"], 1)

    def test_ceo_cockpit_generates_all_fifteen_board_features(self) -> None:
        output = self.tmp / "ceo-cockpit.json"
        payload = generate_ceo_cockpit(self.evidence, analyze_evidence(self.evidence), output)
        required = {
            "executiveOverview",
            "businessImpactEur",
            "decisionQueue",
            "riskOfDoingNothing",
            "operationalOwnership",
            "businessProcessHeatmap",
            "axLegacyRiskIndex",
            "slaBreachForecast",
            "changePortfolioView",
            "boardReadyMonthlyReport",
            "customerOrderImpactSignal",
            "stabilityConfidenceScore",
            "investmentJustification",
            "crisisMode",
            "ceoNarrativeAi",
        }
        self.assertEqual(payload["featureCount"], 15)
        self.assertTrue(required.issubset(payload.keys()))
        self.assertEqual(payload["writePolicy"], "local-files-only-no-db-writes")
        self.assertGreaterEqual(len(payload["decisionQueue"]), 1)
        self.assertTrue(output.exists())
        self.assertTrue((self.tmp / "ceo-board-report.md").exists())

    def test_flight_recorder_incident_markdown_and_feedback_store(self) -> None:
        evidence = self.tmp / "incident-evidence"
        evidence.mkdir()
        (evidence / "ax_live_blocking.csv").write_text(
            "user_id,host_name,session_id,blocking_session_id,program_name,sql_status,database_name,command,wait_type,wait_time_ms,cpu_time_ms,elapsed_time_ms,reads,writes,logical_reads,statement_text,check_time,workload_family,ax_client_type,ax_status\n"
            "user1,AOS1,123,0,Microsoft Dynamics AX,running,AXDB,SELECT,,0,120000,180000,0,0,150000000,\"SELECT SUM(T1.AVAILPHYSICAL) FROM INVENTSUM T1 CROSS JOIN INVENTDIM T2 WHERE T1.INVENTDIMID=T2.INVENTDIMID AND T2.CONFIGID=@P1 AND T2.INVENTSITEID=@P2 AND T2.INVENTLOCATIONID=@P3 AND T2.WMSLOCATIONID=@P4 AND T2.INVENTSTATUSID=@P5\",2026-05-10T08:31:00,AX,Worker,running\n",
            encoding="utf-8",
        )
        feedback = self.tmp / "feedback.json"
        write_feedback(feedback, {"signature": "dummy", "decision": "intentional", "label": "test", "actor": "unit"})
        output = self.tmp / "incident.json"
        markdown = self.tmp / "incident.md"
        payload = build_flight_recorder_report(evidence, output, complaint_text="inventory", feedback_store=feedback, markdown_output=markdown)
        self.assertTrue(markdown.exists())
        self.assertIn("AX Frontend Incident One-Pager", markdown.read_text(encoding="utf-8"))
        self.assertEqual(payload["operatorFeedbackStore"]["entryCount"], 1)
        self.assertIn("spidAxSessionConfidence", payload)

    def test_live_flight_recorder_uses_lightweight_sql_collector(self) -> None:
        script = (SCRIPTS / "collect_lightweight_flight_recorder.ps1").read_text(encoding="utf-8")
        self.assertIn("collect_sql_live_snapshot.ps1", script)
        self.assertNotIn("collect_sql_snapshot.ps1", script)
        live_sql = (SCRIPTS / "collect_sql_live_snapshot.ps1").read_text(encoding="utf-8")
        self.assertIn("sys.dm_exec_requests", live_sql)
        self.assertNotIn("sys.dm_db_index_physical_stats", live_sql)
        self.assertNotIn("dm_db_stats_properties", live_sql)


if __name__ == "__main__":
    unittest.main()
