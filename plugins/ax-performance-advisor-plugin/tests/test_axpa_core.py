import json
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
        self.assertFalse((out / "unit.lock").exists())

    def test_platform_extensions_cover_product_gaps(self) -> None:
        out = self.tmp / "platform"
        payload = generate_platform_extensions(self.evidence, out)
        for key in [
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
        ]:
            self.assertIn(key, payload)
        self.assertTrue((out / "platform-extensions.json").exists())
        self.assertGreaterEqual(payload["recommendationLifecycle"]["items"].__len__(), 1)
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


if __name__ == "__main__":
    unittest.main()
