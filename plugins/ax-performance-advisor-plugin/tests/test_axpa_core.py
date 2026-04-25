import json
import shutil
import tempfile
import unittest
from pathlib import Path

import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from axpa_core import analyze_evidence, build_report, compare_baseline, export_evidence_pack, export_powerbi_dataset
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


if __name__ == "__main__":
    unittest.main()
