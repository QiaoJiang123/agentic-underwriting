import unittest

from backend.services.data_retrieval_service import build_feature_lookup, score_model
from backend.services.decision_workflow_service import get_decision_workflow_record
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


if __name__ == "__main__":
    unittest.main()
