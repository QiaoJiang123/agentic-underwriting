import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from backend.services import chat_action_service
from backend.services import chat_history_service
from backend.services.chat_action_service import parse_chat_action
from backend.services.data_retrieval_service import build_data_retrieval_context, plan_retrieval
from backend.services.document_completeness_service import get_document_completeness_record


class RetrievalAndActionTests(unittest.TestCase):
    def test_task_prompt_selects_tasks_without_default_details(self):
        self.assertEqual(plan_retrieval("what tasks are due this week?"), ["tasks"])

    def test_decision_prompt_selects_decision_workflow(self):
        plan = plan_retrieval("is this account ready to quote and ready to bind?")

        self.assertIn("decision_workflow", plan)
        self.assertIn("analytics", plan)

    def test_retrieval_returns_sources_for_claims(self):
        result = build_data_retrieval_context(
            "001-acme-foods",
            "summarize the claim history",
            file_selection_mode="none",
        )

        self.assertIn("claims", result["plan"])
        self.assertTrue(any(source["skill"] == "claims" for source in result["sources"]))
        tool_contracts = {tool["skill"]: tool for tool in result["selection"]["tool_contracts"]}
        self.assertEqual(tool_contracts["claims"]["required_permission"], "submission:read")

    def test_statistics_prompt_uses_analytics_db(self):
        result = build_data_retrieval_context(
            "001-acme-foods",
            "show claim statistics by broker and associated underwriting decisions",
            file_selection_mode="none",
        )

        self.assertIn("analytics_db", result["plan"])
        self.assertIn("Analytics SQL DB:", result["context"])
        self.assertIn("join both tables on company_id", result["context"])
        self.assertTrue(any(source["skill"] == "analytics_db" for source in result["sources"]))
        self.assertTrue(any(tool["skill"] == "analytics_db" for tool in result["selection"]["tool_contracts"]))

    def test_document_missing_prompt_selects_completeness_even_with_typo(self):
        plan = plan_retrieval("what documnts are missing here?")

        self.assertIn("document_completeness", plan)

    def test_document_completeness_compares_required_to_submitted_metadata(self):
        record = get_document_completeness_record("001-acme-foods")

        self.assertGreaterEqual(record["required_count"], 10)
        self.assertTrue(record["submitted_documents"])
        self.assertIn("required_status", record)

    def test_document_missing_retrieval_includes_required_checklist_source(self):
        result = build_data_retrieval_context(
            "001-acme-foods",
            "what documents are missing here?",
            file_selection_mode="auto",
        )

        self.assertIn("document_completeness", result["plan"])
        self.assertIn("Document Completeness Review:", result["context"])
        self.assertTrue(any(source["skill"] == "document_completeness" for source in result["sources"]))

    def test_auto_document_selection_uses_recent_chat_context_for_followups(self):
        result = build_data_retrieval_context(
            "001-acme-foods",
            "what about that?",
            file_selection_mode="auto",
            conversation_messages=[
                {
                    "role": "user",
                    "content": "Review the ransomware, MFA, EDR, and backup evidence.",
                },
                {
                    "role": "assistant",
                    "content": "I will compare the ransomware supplemental and control documentation.",
                },
                {"role": "user", "content": "what about that?"},
            ],
        )

        selected_files = result["selection"]["document_selection"]["selected_files"]

        self.assertIn("documents", result["plan"])
        self.assertTrue(result["selection"]["document_selection"]["conversation_context_used"])
        self.assertIn("ransomware-supplemental-application.txt", selected_files)
        self.assertIn("mfa-edr-backup-documentation.txt", selected_files)

    def test_auto_document_selection_executes_mcp_tools(self):
        def fake_mcp_tool(tool_name, arguments):
            if tool_name == "select_documents":
                return {
                    "submission_id": arguments["submission_id"],
                    "source": "metadata_rules",
                    "selected_files": ["mfa-edr-backup-documentation.txt"],
                    "selections": [],
                }
            if tool_name == "read_selected_documents":
                return {
                    "submission_id": arguments["submission_id"],
                    "documents": [
                        {
                            "file_name": "mfa-edr-backup-documentation.txt",
                            "file_type": "mfa_documentation",
                            "major_categories": ["cyber_security"],
                            "description": "MFA evidence",
                            "content": "MFA is enabled for email and VPN.",
                        }
                    ],
                }
            raise AssertionError(f"Unexpected MCP tool: {tool_name}")

        with patch("backend.services.data_retrieval_service.call_mcp_tool", side_effect=fake_mcp_tool) as mcp_mock:
            result = build_data_retrieval_context(
                "001-acme-foods",
                "review mfa evidence",
                file_selection_mode="auto",
            )

        document_selection = result["selection"]["document_selection"]
        called_tools = [call.args[0] for call in mcp_mock.call_args_list]

        self.assertEqual(called_tools, ["select_documents", "read_selected_documents"])
        self.assertEqual(document_selection["transport"], "mcp")
        self.assertEqual(document_selection["document_read_transport"], "mcp")
        self.assertIn("Document retrieval source: mcp:metadata_rules.", result["context"])
        self.assertIn("MFA is enabled for email and VPN.", result["context"])

    def test_parse_add_note_action(self):
        action = parse_chat_action("add note: Broker confirmed MFA rollout is complete")

        self.assertEqual(action["type"], "note")
        self.assertIn("MFA rollout", action["text"])

    def test_task_action_returns_created_task_and_ui_target(self):
        created_task = {
            "id": "task-test",
            "title": "Request MFA evidence",
            "due_date": "2026-05-30",
            "status": "open",
        }
        with patch.object(
            chat_action_service,
            "add_task",
            return_value=(
                {"submission_id": "001-acme-foods", "tasks": [created_task]},
                created_task,
            ),
        ), patch.object(chat_action_service, "call_mcp_tool", side_effect=RuntimeError("MCP unavailable")):
            action = chat_action_service.run_chat_action(
                "001-acme-foods",
                "add task: Request MFA evidence due 2026-05-30",
            )

        self.assertEqual(action["type"], "task")
        self.assertEqual(action["created_task"]["id"], "task-test")
        self.assertEqual(action["ui_action"]["panel"], "tasks")
        self.assertEqual(action["transport"], "internal_python_fallback")

    def test_task_action_can_execute_via_mcp(self):
        created_task = {
            "id": "task-mcp",
            "title": "Request MFA evidence",
            "due_date": "2026-05-30",
            "status": "open",
        }
        with patch.object(
            chat_action_service,
            "call_mcp_tool",
            return_value={
                "record": {"submission_id": "001-acme-foods", "tasks": [created_task]},
                "created_task": created_task,
            },
        ) as mcp_mock:
            action = chat_action_service.run_chat_action(
                "001-acme-foods",
                "add task: Request MFA evidence due 2026-05-30",
            )

        mcp_mock.assert_called_once_with(
            "add_scheduled_task",
            {
                "submission_id": "001-acme-foods",
                "title": "Request MFA evidence",
                "due_date": "2026-05-30",
            },
        )
        self.assertEqual(action["created_task"]["id"], "task-mcp")
        self.assertEqual(action["transport"], "mcp")

    def test_task_action_understands_date_then_task_description(self):
        created_task = {
            "id": "task-loss-run",
            "title": "Loss run review",
            "due_date": "2026-05-27",
            "status": "open",
        }
        with patch.object(
            chat_action_service,
            "add_task",
            return_value=(
                {"submission_id": "001-acme-foods", "tasks": [created_task]},
                created_task,
            ),
        ) as add_task_mock, patch.object(chat_action_service, "call_mcp_tool", side_effect=RuntimeError("MCP unavailable")):
            action = chat_action_service.run_chat_action(
                "001-acme-foods",
                "Can you add a task for May 27, 2026. The task should be loss run review.",
            )

        add_task_mock.assert_called_once_with("001-acme-foods", "Loss run review", "2026-05-27")
        self.assertEqual(action["type"], "task")
        self.assertEqual(action["reply"], "Added task due 2026-05-27: Loss run review")

    def test_delete_chat_history_removes_only_matching_file(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history_dir = root / "001-acme-foods"
            history_dir.mkdir(parents=True)
            target = history_dir / "target.json"
            keep = history_dir / "keep.json"
            target.write_text(
                '{"id": "chat-target", "title": "Target", "messages": []}\n',
                encoding="utf-8",
            )
            keep.write_text(
                '{"id": "chat-keep", "title": "Keep", "messages": []}\n',
                encoding="utf-8",
            )

            with patch.object(chat_history_service, "CHAT_HISTORY_DIR", root):
                result = chat_history_service.delete_chat_history("001-acme-foods", "chat-target")

            self.assertTrue(result["deleted"])
            self.assertFalse(target.exists())
            self.assertTrue(keep.exists())

    def test_parse_missing_documents_action_with_typo(self):
        action = parse_chat_action("what documnts are missing here?")

        self.assertEqual(action["type"], "extract_evidence")


if __name__ == "__main__":
    unittest.main()
