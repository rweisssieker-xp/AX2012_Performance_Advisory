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


if __name__ == "__main__":
    unittest.main()
