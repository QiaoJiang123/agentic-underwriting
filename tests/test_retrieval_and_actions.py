import unittest

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

    def test_parse_add_note_action(self):
        action = parse_chat_action("add note: Broker confirmed MFA rollout is complete")

        self.assertEqual(action["type"], "note")
        self.assertIn("MFA rollout", action["text"])

    def test_parse_missing_documents_action_with_typo(self):
        action = parse_chat_action("what documnts are missing here?")

        self.assertEqual(action["type"], "extract_evidence")


if __name__ == "__main__":
    unittest.main()
