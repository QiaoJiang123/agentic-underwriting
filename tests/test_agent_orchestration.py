import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import routes as api_routes
from backend.main import app
from backend.services import agent_trace_service
from backend.services.agent_orchestration_service import run_information_agent


class AgentOrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_information_agent_persists_planner_tool_confidence_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(agent_trace_service, "AGENT_TRACE_DIR", Path(temp_dir)):
                result = run_information_agent(
                    "001-acme-foods",
                    "what documents are missing here?",
                    file_selection_mode="auto",
                )
                traces = agent_trace_service.list_agent_traces("001-acme-foods")

        trace = result["trace"]
        phases = [step["phase"] for step in trace["steps"]]

        self.assertIn("planner", phases)
        self.assertIn("tool_execution", phases)
        self.assertIn("confidence", phases)
        self.assertIn("trace", phases)
        self.assertGreaterEqual(trace["attempt_count"], 1)
        self.assertIn("document_completeness", result["retrieval"]["plan"])
        self.assertTrue(result["retrieval"]["selection"]["tool_contracts"])
        self.assertEqual(len(traces), 1)
        self.assertEqual(traces[0]["trace_id"], trace["trace_id"])

    def test_chat_session_claim_severity_prompt_calls_claim_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(agent_trace_service, "AGENT_TRACE_DIR", Path(temp_dir)),
                patch.object(api_routes, "OPENAI_API_KEY", "sk-test"),
                patch.object(
                    api_routes,
                    "run_underwriting_graph",
                    return_value={
                        "reply": "The open prior claim is high severity and remains under active review.",
                        "response_id": "resp-claim-severity-test",
                    },
                ) as graph_mock,
            ):
                response = self.client.post(
                    "/api/chat",
                    json={
                        "submission_id": "003-evergreen-senior-living",
                        "user_prompt": "What is the severity of the open prior loss and what caused it?",
                        "file_selection_mode": "none",
                        "messages": [
                            {
                                "role": "user",
                                "content": "What is the severity of the open prior loss and what caused it?",
                            }
                        ],
                    },
                )

        payload = response.json()
        model_messages = graph_mock.call_args.kwargs["messages"]
        latest_user_message = model_messages[-1]["content"]
        selected_skills = payload["agent_trace"]["selected_skills"]
        source_skills = {source["skill"] for source in payload["retrieval"]["sources"]}

        self.assertEqual(response.status_code, 200)
        self.assertIn("claims", payload["retrieval"]["plan"])
        self.assertIn("claims", selected_skills)
        self.assertIn("claims", source_skills)
        self.assertIn("Claim System:", latest_user_message)
        self.assertIn("CLM-EVER-2025-001", latest_user_message)
        self.assertIn("High", latest_user_message)
        self.assertIn("Forensics remain open", latest_user_message)

    def test_information_agent_claim_statistics_calls_analytics_db_skill(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(agent_trace_service, "AGENT_TRACE_DIR", Path(temp_dir)):
                result = run_information_agent(
                    "001-acme-foods",
                    "Show claim statistics by broker and associated underwriting decisions.",
                    file_selection_mode="none",
                )

        retrieval = result["retrieval"]
        context = retrieval["context"]
        tool_skills = {
            step["skill"]
            for step in result["record"].get("tool_executions", [])
            if step.get("status") == "done"
        }

        self.assertIn("claims", retrieval["plan"])
        self.assertIn("analytics_db", retrieval["plan"])
        self.assertIn("broker", retrieval["plan"])
        self.assertIn("analytics_db", tool_skills)
        analytics_tool = next(
            step
            for step in result["record"].get("tool_executions", [])
            if step.get("skill") == "analytics_db"
        )
        self.assertEqual(analytics_tool["required_permission"], "analytics:read")
        self.assertEqual(analytics_tool["tool_type"], "read")
        self.assertIn("Analytics SQL DB:", context)
        self.assertIn("join both tables on company_id", context)
        self.assertIn("Broker statistics from joined tables:", context)
        self.assertEqual(
            retrieval["selection"]["analytics_db"]["table_names"],
            ["underwriting_submission_analytics", "claim_analytics"],
        )
        self.assertEqual(retrieval["selection"]["analytics_db"]["claim_primary_key"], "CLM_CLMT_ID")

    def test_information_agent_filters_skills_without_permission(self):
        scoped_context = {
            "user_id": "limited-test",
            "role": "limited",
            "team": "Cyber",
            "permissions": ["submission:read"],
            "submission_scope": ["001-acme-foods"],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(agent_trace_service, "AGENT_TRACE_DIR", Path(temp_dir)):
                result = run_information_agent(
                    "001-acme-foods",
                    "Show claim statistics by broker and associated underwriting decisions.",
                    file_selection_mode="none",
                    auth_context=scoped_context,
                )

        retrieval = result["retrieval"]
        denied = retrieval["selection"]["denied_skills"]

        self.assertIn("claims", retrieval["plan"])
        self.assertNotIn("analytics_db", retrieval["plan"])
        self.assertTrue(any(item["skill"] == "analytics_db" for item in denied))
        self.assertTrue(any(item["skill"] == "broker" for item in denied))


if __name__ == "__main__":
    unittest.main()
