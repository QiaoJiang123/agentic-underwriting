import unittest

from backend.services.data_retrieval_service import build_feature_lookup, score_model
from backend.services.data_retrieval_service import build_data_retrieval_context
from backend.services.decision_package_service import get_decision_package
from backend.services.decision_workflow_service import get_decision_workflow_record
from backend.services.model_governance_service import get_model_governance
from backend.services.model_service import get_model
from backend.services.submission_service import get_submission_detail
from backend.services.underwriting_service import get_underwriting_system_record


class AnalyticsAndDecisionTests(unittest.TestCase):
    def test_quote_model_scores_between_zero_and_one(self):
        submission = get_submission_detail("001-acme-foods")["submission"]
        system = get_underwriting_system_record("001-acme-foods")
        feature_lookup = build_feature_lookup(submission, system)
        scored = score_model(get_model("quote_prob"), feature_lookup)

        self.assertGreaterEqual(scored["probability"], 0)
        self.assertLessEqual(scored["probability"], 1)
        self.assertTrue(scored["steps"])

    def test_decision_workflow_has_four_core_gates(self):
        workflow = get_decision_workflow_record("001-acme-foods")
        gate_keys = {gate["key"] for gate in workflow["gates"]}

        self.assertEqual(
            gate_keys,
            {"quote_readiness", "referral", "quote_approval", "bind_readiness"},
        )

    def test_decision_package_assembles_governed_review_record(self):
        package = get_decision_package("001-acme-foods", "quote")

        self.assertEqual(package["package_type"], "quote")
        self.assertEqual(package["submission_id"], "001-acme-foods")
        self.assertIn("account", package)
        self.assertIn("workflow", package)
        self.assertIn("rating_quote", package)
        self.assertGreaterEqual(package["evidence"]["required_count"], 1)
        self.assertTrue(package["underwriter_controls"])
        self.assertTrue(any(item["source"] == "model/governance.json" for item in package["citations"]))
        governance_names = {model["model_name"] for model in package["model_governance"]["models"]}
        self.assertIn("quote_prob", governance_names)
        self.assertIn("bind_prob", governance_names)

    def test_model_governance_registry_marks_demo_models_not_approved(self):
        registry = get_model_governance()
        quote_governance = get_model_governance("quote_prob")["model"]

        self.assertIn("quote_prob", registry["models"])
        self.assertEqual(quote_governance["approval_status"], "demo_only_not_approved")
        self.assertEqual(quote_governance["decision_owner"], "human_underwriter")
        self.assertTrue(quote_governance["override_required_reason"])

    def test_retrieval_planner_pulls_decision_package_and_governance_context(self):
        result = build_data_retrieval_context(
            "001-acme-foods",
            "Build a quote decision package and explain the model governance limitations.",
            file_selection_mode="none",
        )

        self.assertIn("decision_package", result["plan"])
        self.assertIn("model_governance", result["plan"])
        self.assertIn("Underwriting Decision Package:", result["context"])
        self.assertIn("Model Governance:", result["context"])


if __name__ == "__main__":
    unittest.main()
